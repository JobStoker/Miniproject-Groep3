# https://tutorials-raspberrypi.de/raspberry-pi-laser-lichtschranke-fuer-weite-distanzen/
# https://www.youtube.com/watch?v=8S5C15OnYq8

import RPi.GPIO as GPIO
import os, time

RECEIVER_PIN = 23


def callback_func(channel):
    if GPIO.input(channel):
        print("Lichtschranke wurde unterbrochen")
        # alternativ kann ein Script / Shell Befehl gestartet werden
        # os.system("ls")


if __name__ == '__main__':

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(RECEIVER_PIN, GPIO.IN)
    GPIO.add_event_detect(RECEIVER_PIN, GPIO.RISING, callback=callback_func, bouncetime=200)

    try:
        while True:
            time.sleep(0.5)
    except:
        # Event wieder entfernen mittels:
        GPIO.remove_event_detect(RECEIVER_PIN)