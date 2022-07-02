from time import *
from grovepi import *
from datetime import datetime
from pyrebase import pyrebase
from requests.exceptions import HTTPError
import json

MODULE_DB = "lighting"
DEVICE = "pi-1"

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
        UID = user["localId"]

        print("\nSIGNED IN\n")
        break

db = firebase.database()

old_lights = False
old_brightness = False
countdown = 0
threshold = 600
pir_sensor = 8
light_sensor = 14
living_room_lights1 = 2
living_room_lights2 = 3
living_room_lights3 = 4

pinMode(pir_sensor, "INPUT")
pinMode(light_sensor, "INPUT")
pinMode(living_room_lights1, "OUTPUT")
pinMode(living_room_lights2, "OUTPUT")
pinMode(living_room_lights3, "OUTPUT")


def on_lights(brightness):
    if brightness == 0:
        digitalWrite(living_room_lights1, 0)
        digitalWrite(living_room_lights2, 0)
        digitalWrite(living_room_lights3, 0)
        return False
    elif brightness == 1:
        digitalWrite(living_room_lights1, 1)
        digitalWrite(living_room_lights2, 0)
        digitalWrite(living_room_lights3, 0)
    elif brightness == 2:
        digitalWrite(living_room_lights1, 1)
        digitalWrite(living_room_lights2, 1)
        digitalWrite(living_room_lights3, 0)
    elif brightness == 3:
        digitalWrite(living_room_lights1, 1)
        digitalWrite(living_room_lights2, 1)
        digitalWrite(living_room_lights3, 1)
    return True


def on_schedule(time, start, end):
    if start != end:
        if time == start:
            return True
        elif time == end:
            return False


def sensor(light_intensity, motion, countdown):
    if light_intensity < threshold:
        if motion == 1:
            return True, 5
        elif countdown > 0:
            return None, countdown-1
        else:
            return False, 0
    else:
        return False, 0


while True:
    try:
        sleep(0.5)
        controls = db.child(UID).child(DEVICE).child(MODULE_DB).get()
        for control in controls.each():
            if control.key() == "lights":
                lights = newLights = control.val()
            if control.key() == "brightness":
                brightness = control.val()
            elif control.key() == "schedule":
                schedule = control.val()
                for sch in schedule:
                    if sch == "scheduleStatus":
                        scheduleOn = schedule[sch]
                    if sch == "onTime":
                        onTime = schedule[sch] + ":00"
                    if sch == "offTime":
                        offTime = schedule[sch] + ":00"
            elif control.key() == "sensorMode":
                sensorMode = control.val()

        new_lights = None

        current_time = datetime.now().time()
        current_time_string = current_time.strftime("%H:%M:%S")
        on_time = datetime.strptime(onTime, "%H:%M:%S").time()
        off_time = datetime.strptime(offTime, "%H:%M:%S").time()

        # (On Schedule and On Sensor Mode) or (On Sensor Mode Only)
        if sensorMode and ((scheduleOn and (current_time < on_time or current_time > off_time)) or not scheduleOn):
            sensor_value = analogRead(light_sensor)
            motion_value = digitalRead(pir_sensor)
            new_lights, countdown = sensor(
                sensor_value, motion_value, countdown)
            print("Sensor Mode On", "\n--------------", "\nLight Sensor value: %d" % (sensor_value),
                  "\nCountdown         :", countdown, "\n")

        # On Schedule
        elif scheduleOn:
            new_lights = on_schedule(current_time_string, onTime, offTime)
            print("Schedule On", "\n-----------", "\nCurrent Time:", current_time_string,
                  "\nOn Time     :", onTime, "\nOff Time    :", offTime, "\n")

        # Check sensor mode status
        if countdown > 0 and not sensorMode:
            new_lights = False

        # Check lights status
        if (old_lights != lights or new_lights is not None) and not sensorMode \
                and (not scheduleOn or (scheduleOn and current_time_string != onTime and current_time_string != offTime)):
            new_lights = lights
            #print("Schedule Status:", scheduleOn, "\n\nSensor Mode Status:", sensorMode)

        # On lights
        if new_lights is not None or old_brightness != brightness:
            if new_lights:
                on_lights(brightness)
            else:
                on_lights(0)

            # Update new_lights to NEXT LOOP's old_lights
            old_lights = new_lights
            old_brightness = brightness

            # Update lights
            if new_lights is not None:
                db.child(UID).child(DEVICE).child(MODULE_DB).update({
                    "lights": new_lights
                })

    except KeyboardInterrupt:
        on_lights(0)
        break
    except TypeError:
        print("Type Error")
    except IOError:
        print("IO Error")
