from time import *
from grovepi import *
from grove_rgb_lcd import *
from PIL import Image
from pyrebase import pyrebase
from luma.core.interface.serial import i2c, spi
from luma.oled.device import sh1106
from requests.exceptions import HTTPError
import json

AUTH_EMAIL = "pi1@aether-iot.web.app"
AUTH_PASSWORD = "123456"



config = {
    "apiKey": "AIzaSyBb__72a_Y7ruiHQiG9gGK0qUmrbnESVvE",
    "authDomain": "aether-iot.firebaseapp.com",
    "databaseURL": "https://aether-iot.firebaseio.com",
   "storageBucket": "aether-iot.appspot.com"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()

# Firebase login
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

        print("\nSIGNED IN\n")
        break

db = firebase.database().child(uid).child("pi-1").child("Temperature")

serial = i2c(port=1, address=0x3C)
oled = sh1106(serial, rotate=0, height=128)

relay1 = 2
relay2 = 3
relay3 = 4
dhtsensor = 14
pinMode(dhtsensor, "INPUT")
pinMode(relay1, "OUTPUT")
pinMode(relay2, "OUTPUT")
pinMode(relay3, "OUTPUT")

def displayImage(weather) :
    img = Image.open(weather).resize((128, 128)).convert("1")
    oled.display(img)

def detectTemperature() :
    [temp, hum] = dht(dhtsensor, 0)
    if temp > 30:
        setRGB (255, 100, 0)
    elif temp > 20:
        setRGB (128, 128, 128)
    else:
        setRGB(0, 255, 255)
    t = str(temp)
    setText("Temp=" + t)
    return temp

def detectWeather(temp) :
    if temp > 30:
        displayImage("Sunny.png")
    elif temp > 20:
        displayImage("Cloudy.png")
    else:
        displayImage("Rainy.png")

def fanSpeed(temp, manual, speed, power):
    if manual:
        if not power:
            speed = 0
        else:
            setFanSpeed(speed)
    else:
        if temp > 30:
            speed = 3
        elif temp > 20:
            speed = 2
        else:
            speed = 1

    return setFanSpeed(speed)

def setFanSpeed(speed):
    if speed == 0:
        digitalWrite(relay1, 0)
        digitalWrite(relay2, 0)
        digitalWrite(relay3, 0)
    elif speed == 1:
        digitalWrite(relay1, 1)
        digitalWrite(relay2, 0)
        digitalWrite(relay3, 0)
    elif speed == 2:
        digitalWrite(relay1, 1)
        digitalWrite(relay2, 1)
        digitalWrite(relay3, 0)
    elif speed == 3:
        digitalWrite(relay1, 1)
        digitalWrite(relay2, 1)
        digitalWrite(relay3, 1)
    return speed

while True:
    try:
        sleep(1)
        database = db.get()
        for attribute in database:
            if attribute.key() == "FanSpeed":
                attribute.val()

        database["Power"]
        database["FanSpeed"]
        database["Manual"]

        temp = detectTemperature()
        detectWeather(temp)
        speed = fanSpeed(temp, manual, speed, power)

        db = firebase.database().child(uid).child("pi-1").child("Temperature")
        db.update({
            "FanSpeed": speed,
            "Temperature": temp
        })
    except KeyboardInterrupt:
        setText("Program Exited")
        break
    except TypeError:
        print("Type Error occurs")
    except IOError:
        print("IO Error occurs")
