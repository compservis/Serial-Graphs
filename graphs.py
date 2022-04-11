# Show graphs

DEBUG_TEST = True

import time
import pandas as pd
from pathlib import Path

import serial
import threading
import json
import os
import random
from multiprocessing.connection import Listener
from pymemcache.client import base

try:
    ser = serial.Serial("/dev/ttyS0", 9600)
except:
    print('Unable to open Serial')
    ser = ''

global log
global last_log
global new_data_available
global new_data
global df
global css



new_data_available = False
shared = base.Client(('localhost', 11211))
try:
    shared.set('new_data', 0)
    shared.set('data', '')
    shared.set('sensor', '')
except:
    print('WARNING/Graphs: Cannot set new_data flag')

last_log = pd.DataFrame({
    'Time': [],
    'Temperature': [],
    'Pressure': [],
    'Sensor': []
    })

df = last_log

address = ('localhost', 6000)

def notify_new_data(d, s):
    global new_data_available
    global cs
    new_data_available = True
    # Shared var
    try:
        shared.replace('new_data', 1)
        shared.replace('data', d)
        shared.replace('sensor', s)
    except:
        print('WARNING/Graphs: Cannot set new_data flag')

def handle_data(data, sen):
    global new_data_available
    global new_data
    print(data)
    new_data = json.loads(data)
    new_data["type"] = chr(new_data["type"])
    notify_new_data(new_data, sen)


def write_to_port(ser):
    global cs
    cs = 0
    while True:
        if (cs == 3):
            cs = 0
        css = str(cs)
        ser.write(css.encode('ascii'))
        print(css)
        cs += 1
        time.sleep(2)


def read_from_port(ser):
    global css
    cs = 1
    while True:
        if not DEBUG_TEST:
            try:
                reading = ser.readline().decode()
            except:
                pass
        else:
            ## TEST PART
            r = {'type': 84, 'reading': round(random.uniform(17.2, 23.5), 2)}
            reading = json.dumps(r)
            if (cs == 21):
                cs = 1
            css = str(cs)
            print(css)
            r = json.loads(reading)
            r.update({'sensor': css})
            reading = json.dumps(r)
            ############
            
        handle_data(reading, cs)

        cs += 1
        time.sleep(0.5)


def update_logs():
    global log
    global last_log
    global new_data_available
    global new_data
    global df
    global css

    while True:
        if new_data_available:
            print('New data:', new_data)
            # check for today's log presence
            date = time.strftime("%d%b%y", time.localtime())
            tim = time.strftime("%H:%M:%S", time.localtime())
            todays_log_path = date + ".csv"
            todays_log = Path(todays_log_path)

            df = pd.DataFrame({
                'Time': [tim],
                'Type': [new_data['type']],
                'Reading': [new_data['reading']],
                'Sensor': [new_data['sensor']]
            })
            if todays_log.is_file():
                # read log
                df.to_csv(todays_log_path, mode='a', header=False, index=False)
                log = pd.read_csv(todays_log_path)
                last_log = pd.read_csv(todays_log_path)
                last_log.append(df)
            else:
                # create log file
                log = df
                log.to_csv(todays_log_path, index=False)

            last_log = last_log[-20:]
            new_data_available = False


thread0 = threading.Thread(target=read_from_port, args=(ser,))
thread2 = threading.Thread(target=update_logs)

thread0.start()
thread2.start()
