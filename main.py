import json
from time import sleep, time, ticks_ms

from machine import Pin, I2C

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
    
from uosc.server import split_oscstr, parse_message

from rhb_pico_utils import run_server, toggle_startup_display, wifi_connection
import rhb_pico_utils
import patterns

import network

from neopixel import Neopixel
 
pixels = Neopixel(1, 0, 28, "GRB")

VIOLET = (255, 0, 255)
ORANGE = (255, 50, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
 
pixels.brightness(75)
pixels.fill(RED)
pixels.show()

solenoids = [Pin(0, Pin.OUT),
             Pin(1, Pin.OUT),
             Pin(2, Pin.OUT),
             Pin(3, Pin.OUT),
             Pin(4, Pin.OUT),
             Pin(5, Pin.OUT),
             Pin(6, Pin.OUT),
             Pin(7, Pin.OUT)]
[x.off() for x in solenoids]

def activate_ap_mode():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="tiki-control", password="breakson")


async def handle_osc(data, src, dispatch=None, strict=False):
    """Process any new OSC messages about gesture"""
    print("X")
    try:
        head, _ = split_oscstr(data, 0)
        if head.startswith('/'):
            messages = [(-1, parse_message(data, strict))]
        elif head == '#bundle':
            messages = parse_bundle(data, strict)
    except Exception as exc:
        print(f"Exception in handle_osc parsing: {exc}")
        return

    try:
        for timetag, (oscaddr, tags, args) in messages:
            if (("gesture" not in oscaddr) and ("initialized" not in oscaddr)):
                print(f"{time()} Unknown OSC message : {oscaddr} {tags} {args}")
                continue

            if "gesture" in oscaddr:
                pixels.fill(RED)
                pixels.show()
                pattern = patterns.pattern_dict[args[0]]
                print(args[0])
                for i in pattern:
                    print(f'{ticks_ms()} - 0b{i[0]:08b}')
                    states = i[0]
                    start = ticks_ms()
                    [solenoids[j].on() if states & (1 << j) else solenoids[j].off() for j in range(8)]
                    while ticks_ms() < (start + i[1]):
                        continue
                pixels.fill(BLUE)
                pixels.show()        
            elif "initialized" in oscaddr:
                if int(args[0]):
                    pixels.fill(GREEN)
                else:
                    pixels.fill(BLUE)
                pixels.show()
            if __debug__:
                print(f"{time()} OSC message : {oscaddr} {tags} {args}")

            if dispatch:
                dispatch(timetag, (oscaddr, tags, args, src))
    except Exception as exc:
        print(f"Exception in handle_osc process message: {exc} {data} {src}")


async def main_loop():
    """Main async loop"""
    try:
        print("Starting main loop...")
        server_task = asyncio.create_task(run_server("192.168.4.1", 8888, handle_osc))
        await server_task
    except:
        rhb_pico_utils.reboot()


if __name__ == "__main__":
            
    rhb_pico_utils.led = Pin("LED", Pin.OUT)
    rhb_pico_utils.led.off()

    activate_ap_mode()

    pixels.fill(BLUE)
    pixels.show()
    rhb_pico_utils.led.on()

    try:
        asyncio.run(main_loop())
    except Exception as exc:
        print(f"Exception in top loop: {exc}")
        rhb_pico_utils.reboot()
    rhb_pico_utils.reboot()
    

    