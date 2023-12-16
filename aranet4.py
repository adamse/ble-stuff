import struct
import enum
import asyncio
import datetime

from bleak import BleakScanner
from bleak.assigned_numbers import AdvertisementDataType

import duckdb

import pandas

# https://bitbucket.org/bluetooth-SIG/public/src/c814314dfbc0ea311424ad9a80a7cdb8efdc1c3c/assigned_numbers/company_identifiers/company_identifiers.yaml#lines-4809
mfg_id = 0x0702

# ??
uuid = '0000fce0-0000-1000-8000-00805f9b34fb'

# ref https://github.com/Anrijs/Aranet4-Python/blob/master/aranet4/client.py#L263

# AdvertisementData(local_name='Aranet4 20D17', manufacturer_data={1794: b'!\x03\x02\x01\x00\x0c\x0f\x01\xb2\x04\xb8\x01b(2a\x02x\x00@\x00}'}, service_uuids=['0000fce0-0000-1000-8000-00805f9b34fb'], rssi=-73)
# 21 03 02 01 00 0c 0f 01 b2 04 b8 01 62 28 32 61 02 78 00 40 00 7d

def print_info(d, adv):
    print(f'{d.address}: {d.name}')
    raw = adv.manufacturer_data[mfg_id]
    status = decode_status(raw)
    print(status)
    payload = decode_payload(raw)
    print(payload)

def decode_status(raw):
    b, *v = struct.unpack('<BBBB', raw[0:4])
    v.reverse()
    return {
        'disconnected': bool(b & 1),
        'calibration_state': (b >> 2) & 0x3,
        'dfu_active': bool((b >> 4) & 1),
        'integrations': bool((b >> 5) & 1),
        'version': f'{v[0]}.{v[1]}.{v[2]}',
    }

class Status(enum.IntEnum):
    NONE = 0
    GREEN = 1
    AMBER = 2
    RED = 3
    BLUE = 4

def decode_payload(raw):
    if len(raw) < 20:
        return

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

class Logger:
    def __init__(self):
        pass

    def __call__(self, d, adv):
        # wait for scan response data
        if adv.manufacturer_data is None:
            return
        # no data?
        if not mfg_id in adv.manufacturer_data:
            return

        raw = adv.manufacturer_data[mfg_id]
        status = decode_status(raw)
        payload = decode_payload(raw)
        print(d)
        print(status)
        print(payload)

class DbLogger:
    def __init__(self, con):
        self.con = con

    def __call__(self, d, adv):
        # wait for scan response data
        if adv.manufacturer_data is None:
            return
        # no data?
        if not mfg_id in adv.manufacturer_data:
            return

        time = datetime.datetime.utcnow()
        raw = adv.manufacturer_data[mfg_id]
        status = decode_status(raw)
        payload = decode_payload(raw)
        data = {'time': time, **status, **payload}
        df = pandas.DataFrame(data, index=[0])
        try:
            self.con.append('aranet4', df)
        except:
            self.con.sql('create table aranet4 as select * from df')

async def main2():
    stop_event = asyncio.Event()
    async with BleakScanner(
            detection_callback=Logger(),
            # service_uuids=[uuid],
            scanning_mode='passive',
            # (match start position, payload type, bytes to match (here the mfg id))
            bluez={'or_patterns': [(0, AdvertisementDataType.MANUFACTURER_SPECIFIC_DATA, struct.pack("<H", mfg_id))]},
        ) as scanner:
        await stop_event.wait()

async def main3():
    stop_event = asyncio.Event()
    with duckdb.connect('data.db') as con:
        async with BleakScanner(
                # detection_callback=Logger(),
                detection_callback=DbLogger(con),
                # service_uuids=[uuid],
                scanning_mode='passive',
                # (match start position, payload type, bytes to match (here the mfg id))
                bluez={'or_patterns': [(0, AdvertisementDataType.MANUFACTURER_SPECIFIC_DATA, struct.pack("<H", mfg_id))]},
            ) as scanner:
            await stop_event.wait()

asyncio.run(main2())
