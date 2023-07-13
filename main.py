from machine import Pin, PWM
from time import sleep
import time
from random import randint
import uasyncio as asyncio
import socket
import network
import esp
import gc
import re
import ntptime

points = 0
points_to_win = 5

btns = [Pin(12, Pin.IN), Pin(2, Pin.IN), Pin(4, Pin.IN)]
btn_states = [False] * 3

leds = [Pin(27, Pin.OUT), Pin(14, Pin.OUT), Pin(5, Pin.OUT)]

buzzer = PWM(Pin(23))
buzzer.init(freq=440, duty=0)
duty = 216

led_sequence = []
seq_index = 0
shown_sequence = False

def led_on(index):
    global leds
    
    if not leds[index].value():
        leds[index].on()

def led_off(index):
    global leds
    
    if leds[index].value():
        leds[index].off()

def win_round():
    global seq_index, points
    
    add_led()
    seq_index = 0
    points += 1
    
def reset():
    global seq_index, points, led_sequence, shown_sequence
    
    seq_index = 0
    shown_sequence = False
    points = 0
    led_sequence = []
    add_led()

def add_led():
    global led_sequence
    
    led_sequence.append(randint(0, 2))

def on_btn_press(index):
    global led_sequence, seq_index, shown_sequence
    
    print(str(index) + " pressed")
    print(led_sequence)

    if(index == led_sequence[seq_index]):
        seq_index += 1
        if seq_index == len(led_sequence):
            shown_sequence = False
            win_round()
    else:
        reset()
    
def on_btn_release(index):
    print(str(index) + " released")

def handle_input():
    global btn_states
    
    for i in range(3):
        btn_state = btns[i].value()

        if btn_states[i] == False and btn_state == True:
            btn_states[i] = True            
            on_btn_press(i)
        elif btn_states[i] == True and btn_state == False:
            btn_states[i] = False
            on_btn_release(i)

async def show_sequence():
    global shown_sequence, led_sequence
    
    for i in led_sequence:
        led_on(i)
        await asyncio.sleep_ms(1000)
        led_off(i)

    shown_sequence = True
    
async def alarm():
    while points < points_to_win:
        buzzer.duty(duty)
        asyncio.ms_sleep(500)
        buzzer.duty(0)
        asyncio.ms_sleep(500)

    buzzer.duty(duty)
    asyncio.ms_sleep(150)
    buzzer.freq(378)
    asyncio.ms_sleep(150)
    buzzer.duty(0)

async def game():
    print("start loop")
    buzzer.duty(duty)
    start_btn = Pin(18, Pin.OUT)
    
    while not start_btn.value():
        await asyncio.ms_sleep(100)
    
    add_led()
    
    while points < points_to_win:    
        if not shown_sequence:
            await show_sequence()
    
        handle_input()
        await asyncio.ms_sleep(100)
        
    buzzer.duty(0)

class ESPServer:
    def __init__(self):
        esp.osdebug(None)
        gc.collect()
        self.station = network.WLAN(network.STA_IF)
        self.station.active(True)

    def connect(self, ssid, password):
        self.station.connect(ssid, password)
        while not self.station.isconnected():
          pass
        print('Connection successful')
        print(self.station.ifconfig())

    def web_page(self):
        html = """<html><head><title>Alarme</title><meta charset="UTF-8" /> <meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><style>html{font-family:Helvetica;display:inline-block;margin:0 auto;text-align:center} h1{color:#0f3376;padding:2vh}p{font-size:1.5rem} .time-selector{font-size:3rem;border-radius:20px} .submit-btn{font-size:2rem;border-radius:10px}</style></head><body><h1>Alarme Simon</h1><p>Selecione o horário do despertador:</p><form action="/"><input type="time" name="time" class="time-selector"><br><br><input type="submit" value="Enviar" class="submit-btn"></form></body><script>document.getElementById('form').addEventListener("submit", event => {
				event.preventDefault()
				let data = JSON.stringify({
					"time": document.getElementById("time-selector").value() 
				});
				const xhttp = new XMLHttpRequest()
				xhttp.overrideMimeType("application/json")
				xhttp.open("POST", '/time', true)
				xhttp.send(data)
			});</script></html>"""
        return html
                
    def start(self):
        # Inicialização do socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 3000))
        s.listen(2)
        while True:
            conn, addr = s.accept()
            print('Got a connection from %s' % str(addr))
            request = conn.recv(1024)
            request = str(request)
            print('Content = %s' % request)
            match = re.search("time=([\d\w%]+)", request)

            if match:
                time_str = match.group(1)
        
                alarm_hour = int(time_str[0:2])
                alarm_minute = int(time_str[-2:])
            
                actual_time = time.localtime(time.time())
            
                hour = int(actual_time[3])
                minute = int(actual_time[4])
                
                elapsed_seconds = hour * 60 * 60 + minute * 60
                elapsed_alarm_seconds = alarm_hour * 60 * 60 + alarm_minute * 60
                
                seconds_until_alarm = abs(elapsed_alarm_seconds - elapsed_seconds)
                
                if(elapsed_alarm_seconds < elapsed_seconds):
                    seconds_until_alarm += 24 * 60 * 60
                
                await asyncio.sleep(seconds_until_alarm)

                loop = asyncio.get_loop()

                tasks = [loop.create_task(game()), loop.create_task(alarm())]

                loop.run_until_complete(asyncio.wait(tasks))

                loop.close()
                     
            response = self.web_page()
            conn.send('HTTP/1.1 200 OK\n')
            conn.send('Content-Type: text/html\n')
            conn.send('Connection: close\n\n')
            conn.sendall(response)
            conn.close()

server = ESPServer()
server.connect("Luis A23", "rotLu032005")
server.start()