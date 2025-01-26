from time import sleep, ticks_ms

import machine
import network

import usocket as socket

import uselect as select

import uasyncio as asyncio

display: HT16K33Segment = None
led: machine.Pin = None

MAX_DGRAM_SIZE = 6000


def reboot():
    """Reset the machine"""
    sleep(5)
    machine.reset()


def toggle_startup_display(count):
    """Indicate progress on the display"""
    if count % 6 == 0:
        sync_text = b"\x01\x01\x01\x01"
    elif count % 6 == 1:
        sync_text = b"\x02\x02\x02\x02"
    elif count % 6 == 2:
        sync_text = b"\x04\x04\x04\x04"
    elif count % 6 == 3:
        sync_text = b"\x08\x08\x08\x08"
    elif count % 6 == 4:
        sync_text = b"\x10\x10\x10\x10"
    elif count % 6 == 5:
        sync_text = b"\x20\x20\x20\x20"
    for i in range(len(sync_text)):
        display.set_glyph(sync_text[i], i)
    display.draw()


def wifi_connection(config):
    """Connect to the wifi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    while True:
        wait = 0
        wlan.connect(config["WIFI_SSID"], config["WIFI_PASSWORD"])
        while wait < 12:
            status = wlan.status()
            if status >= 3:
                break
            wait += 1
            sleep(1)
        if wlan.status() != 3:
            print(f'network connection failed, retrying {wlan.status()}')
            return None
        else:
            print('connected')
            status = wlan.ifconfig()
            print('ip = ' + status[0])
            break
    return wlan


async def run_server(saddr, port, handler):
    """Run the OSC Server asynchronously"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ai = socket.getaddrinfo(saddr, port)[0]
        sock.setblocking(False)
        sock.bind(ai[-1])
        p = select.poll()
        p.register(sock, select.POLLIN)
        poll = getattr(p, "ipoll", p.poll)

        print(f"Listening for OSC messages on {saddr}:{port}")
        while True:
            try:
                for res in poll(1):
                    if res[1] & (select.POLLERR | select.POLLHUP):
                        print("UDPServer.serve: unexpected socket error.")
                        break
                    elif res[1] & select.POLLIN:
                        buf, addr = sock.recvfrom(MAX_DGRAM_SIZE)
                        asyncio.create_task(handler(buf, addr))
                #print(1)
                await asyncio.sleep(0)
                #print(2)
            except Exception as e:
                print(f"Exception in run_server: {e}")
                break
        sock.close()
    except Exception as e:
        print(f"Exception in run_server top: {e}")
