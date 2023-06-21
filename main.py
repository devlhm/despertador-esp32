from machine import Pin
from time import sleep

btns = [Pin(14, Pin.IN), Pin(27, Pin.IN), Pin(26, Pin.IN)]
leds = [Pin(18, Pin.IN), Pin(19, Pin.IN), Pin(21, Pin.IN)]

btn_states = [False] * 3

def handle_btn_press():
    for i in range(3):
        btn_state = btns[i].value()

        if btn_states[i] == False and btn_state == True:
            print("pressed")

while True:
    handle_btn_press()

    sleep(1)