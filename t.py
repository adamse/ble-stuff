import struct
import enum
import asyncio

from bleak import BleakScanner

mfg_id = 1794
uuid = '0000fce0-0000-1000-8000-00805f9b34fb'

# ref https://github.com/Anrijs/Aranet4-Python/blob/master/aranet4/client.py#L263

def print_info(d, adv):
    print(f'{d.address}: {d.name}')
    raw = adv.manufacturer_data[mfg_id]
    info = decode_configuration(raw)
    print(info)
    if len(raw) >= 20:
        payload = decode_payload(raw)
        print(payload)

def decode_configuration(raw):
    b, *v = struct.unpack('<BBBB', raw[0:4])
    v.reverse()
    return {
        'disconnected': bool(b & 1),
        'calibration_state': (b >> 2) & 0x3,
        'dfu_active': bool((b >> 4) & 1),
        'integrations': bool((b >> 5) & 1),
        'version': v,
    }

class Status(enum.IntEnum):
    NONE = 0
    GREEN = 1
    AMBER = 2
    RED = 3
    BLUE = 4

def decode_payload(raw):
    co2, temp, pressure, hum, batt, status, ival, since = struct.unpack('<HHHBBBHH', raw[8:21])
    co2_bad = co2 >> 15 & 1
    temp_bad = temp >> 14 & 1
    pressure_bad = pressure >> 15 & 1
    hum_bad = hum >> 8 & 1
    return {
        'co2': co2 if not co2_bad else -1,
        'temp': round(float(temp) * 0.05, 2) if not temp_bad else -1,
        'pressure': round(float(pressure) * 0.1, 2) if not pressure_bad else -1,
        'humidity': hum if not hum_bad else -1,
        'battery': batt,
        'status': Status(status),
        'interval': ival,
        'since': since,
    }

class CB:
    def __init__(self, events, stop):
        self.events = events
        self.count = 0
        self.stop = stop

    def __call__(self, d, adv):
        # wait for scan response data
        if adv.manufacturer_data is None:
            print("no data")
            return
        print_info(d, adv)
        self.count = self.count + 1
        if self.count == self.events:
            self.stop.set()

async def main2():
    stop_event = asyncio.Event()

    async with BleakScanner(
            detection_callback=CB(10, stop_event),
            service_uuids=[uuid],
        ) as scanner:
        await stop_event.wait()

asyncio.run(main2())
