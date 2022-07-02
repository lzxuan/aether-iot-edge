# GrovePi
from grovepi import *

# Firebase wrapper
from pyrebase import pyrebase

# Password input
from getpass import getpass

# Firebase login error handling
from requests.exceptions import HTTPError
import json

# QR code
import qrcode

# OLED display
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106

# Datetime for logging
from datetime import datetime

# WebRTC
import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer
import platform
from threading import Thread

# sleep
from time import sleep


# Firebase configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyBb__72a_Y7ruiHQiG9gGK0qUmrbnESVvE",
    "authDomain": "aether-iot.firebaseapp.com",
    "databaseURL": "https://aether-iot.firebaseio.com",
    "storageBucket": "aether-iot.appspot.com"
}
DEVICE = "pi-1"
SECURITY = "security"
SDP = "sdp"
WEB_DOMAIN = "aether-iot.web.app"

# Firebase initialization
firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
auth = firebase.auth()
db = firebase.database()

# Peer connections for WebRTC
pcs = set()

# OLED panel initialization
serial = i2c(port=1, address=0x3C)
oled = sh1106(serial, rotate=1, height=128)

# GrovePi pin configuration
buzzer = 2
led = 3
lock = 4

# GrovePi pin initialization
pinMode(buzzer, "OUTPUT")
pinMode(led, "OUTPUT")
pinMode(lock, "OUTPUT")


# Firebase login + QR code generation
while True:
    try:
        print("=================================\n"
              " Aether IoT | Sign in with email \n"
              "=================================")
        # email = input(     "Email   : ")
        # password = getpass("Password: ")
        print("Email   : gujyzxozcvxsduljtv@mhzayt.com")
        print("Password: ")
        email = password = "gujyzxozcvxsduljtv@mhzayt.com"
        user = auth.sign_in_with_email_and_password(email, password)
    except HTTPError as error:
        error_json = error.args[1]
        error_msg = json.loads(error_json)["error"]["message"]
        print("\n [!] %s\n" % error_msg.replace("_", " "))
    else:
        uid = user["localId"]

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=1
        )
        qr.add_data(WEB_DOMAIN + "/m/" + uid)
        qr_img = qr.make_image().resize((128, 128)).convert("1")

        print("\nSIGNED IN\n")
        break


# log with datetime
def log(component, *args):
    print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
          "[%s]" % component, " ".join(args))


# set alarm state
def setAlarm(on=False):
    if on:
        log("CTRL", "alarm on")
        digitalWrite(buzzer, 1)
        digitalWrite(led, 1)
    else:
        log("CTRL", "alarm off")
        digitalWrite(buzzer, 0)
        digitalWrite(led, 0)


# set lock state
def setLock(locked=True):
    if locked:
        log("CTRL", "door locked")
        digitalWrite(lock, 0)
    else:
        log("CTRL", "door unlocked")
        digitalWrite(lock, 1)


# set QR code display state
def displayQR(display=True):
    if display:
        log("MSG", "QR showing")
        oled.display(qr_img)
    else:
        log("MSG", "QR hiding")
        oled.clear()


# reply with answer to offerer in WebRTC
async def answer(sdp):
    log("SDP", "offer received")
    offer = RTCSessionDescription(sdp=sdp["sdp"], type=sdp["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        log("ICE", "%s" % pc.iceConnectionState)
        if pc.iceConnectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    options = {"framerate": "5", "video_size": "640x480"}
    if platform.system() == "Darwin":
        player = MediaPlayer(
            "default:none", format="avfoundation", options=options)
    else:
        player = MediaPlayer("/dev/video0", format="v4l2", options=options)

    await pc.setRemoteDescription(offer)

    for t in pc.getTransceivers():
        if t.kind == "audio" and player.audio:
            pc.addTrack(player.audio)
        elif t.kind == "video" and player.video:
            pc.addTrack(player.video)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    sdp_ref = db.child(uid).child(DEVICE).child(SECURITY).child(SDP)
    sdp_ref.set({"sdp": pc.localDescription.sdp,
                 "type": pc.localDescription.type}, user["idToken"])
    log("SDP", "answer sent")


# close all peer connections in WebRTC
async def close_all_connections():
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


# run coroutine in daemon thread
def run_coro_in_thread(coro):
    loop = asyncio.new_event_loop()
    Thread(target=loop.run_forever, daemon=True).start()
    asyncio.run_coroutine_threadsafe(coro, loop)


# handle Firebase security database stream
def stream_handler(message):
    if message["event"] == "put":
        path = message["path"]
        data = message["data"]
        if path == "/sdp":
            if data["type"] == "offer":
                run_coro_in_thread(answer(data))
        elif path == "/control/alarm":
            setAlarm(data)
        elif path == "/control/lock":
            setLock(data)
        elif path == "/displayQR":
            displayQR(data)
        elif path == "/":
            for key in data:
                if key == "sdp" and data[key]["type"] == "offer":
                    run_coro_in_thread(answer(data["sdp"]))
                elif key == "control":
                    for ckey in data[key]:
                        if ckey == "alarm":
                            setAlarm(data[key][ckey])
                        elif ckey == "lock":
                            setLock(data[key][ckey])
                elif key == "displayQR":
                    displayQR(data[key])


# stream for Firebase security database changes
def security_db_stream():
    security_ref = db.child(uid).child(DEVICE).child(SECURITY)
    return security_ref.stream(stream_handler, user["idToken"])


# refresh login token every 59 minutes
def refresh_token():
    while True:
        sleep(59 * 60)
        user = auth.refresh(user["refreshToken"])


if __name__ == "__main__":
    try:
        log("PROG", "program started")
        s = security_db_stream()
        refresh_token()
    except KeyboardInterrupt:
        asyncio.run(close_all_connections())
        s.close()
        log("PROG", "program exited")
