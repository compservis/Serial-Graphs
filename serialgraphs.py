# serialgraphs.py
# Get list of serial ports and get data from one to plot graph

import PySimpleGUI as sg
import sys
import glob
import serial
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as anim
import numpy as np
import pandas as pd
import threading
import json
import time
from datetime import datetime

global new_data_available
global new_data
global ser
global thread0
global df
global should_read
global selected

is_reading = False
should_read = False

new_data = {}
new_data_available = False

selected = " "

registered_sensors = []

matplotlib.use("TkAgg")
sg.ChangeLookAndFeel('Black')

screen_size = sg.Window.get_screen_size()
screen_dpi = 80
px = 1/screen_dpi
print(screen_size[0], screen_size[1], px)

emp = {'s':[0], 'd':[0]}
df = pd.DataFrame({
        'Time': [],
        'Sensor': [],
        'Value': []
        })

def draw_figure(canvas, figure, loc=(0, 0)):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side="top", fill="both", expand=1)
    return figure_canvas_agg

def main():
    ports = serial_ports()
    global new_data_available
    global new_data
    global ser
    global selected

    plt.style.use('dark_background')
    plt.rc('grid', linestyle="-", color='0.2')
    plt.rc('font',**{'family':'monospace','monospace':['JetBrains Mono']})

    col1 = [
        [sg.T("Serial port", font=("JetBrains Mono", 12))],
        [sg.B("UPD", font=("JetBrains Mono", 10), key="-UPD-"), sg.InputCombo(tuple(ports), size=(40,1), key="-SERIAL-")],
    ]

    col2 = [
        [sg.B("Start", key="-DRAW-", size=(12,5))], 
        [sg.B("Stop", key="-STOP-")],
    ]

    col3 = [
        [sg.T("Sensors", font=("JetBrains Mono", 12))],
        [sg.Listbox(values=registered_sensors, size=(12,5), key="-LIST-", enable_events=True)],
    ]

    layout = [
        [sg.Canvas(key=("GRAPH_CANVAS"))], 
        [sg.Column(col1), sg.VSeparator(), sg.Column(col2), sg.VSeparator(), sg.Column(col3)],
    ]

    fig = matplotlib.figure.Figure(figsize=(12,8), dpi=screen_dpi)
    ax = fig.add_subplot(111)
    fig.tight_layout()
    ax.cla()
    

    window = sg.Window("Ports", layout, font=("JetBrains Mono", 14), resizable=True,finalize=True)
    window.bind('<Configure>',"Configure")

    fig_add = draw_figure(window["GRAPH_CANVAS"].TKCanvas, fig)

    while True:
        event, values = window.read(250)

        if new_data_available:
            window["-LIST-"].Update(registered_sensors)
            if len(values["-LIST-"]) == 1:
                selected = values["-LIST-"][0]
            p = df.loc[df["Sensor"] == selected]
            draw(ax, fig, p)
            fig_add.draw()
            new_data_available= False

        if event == "-UPD-":
            if not is_reading:
                ports = serial_ports()
                window["-SERIAL-"].Update(values=tuple(ports))
        if event == '-STOP-':
            stop_monitoring()

        if event == '-LIST-':
            selected = values['-LIST-'][0]

        if event is sg.WIN_CLOSED:
            break
        if event == '-DRAW-':
            ser = values["-SERIAL-"]
            print(ser)
            if ser != '':
                start_monitoring(serial.Serial(ser, 9600))
        if event == 'Configure':
            print(window.size)
            if window.TKroot.state() == 'zoomed':
                print('Window zoomed and maximized')
            else:
                print('Window normal')

    stop_monitoring()
    window.close()


def draw(ax, fig, d):
    ax.cla()
    ax.grid(True)
    fig.tight_layout()
    ax.plot(d['Time'], d['Value'], color='red')


def serial_ports():
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    print(result)
    return result


def read_from_port(ser):
    while True:
        if should_read:
            try:
                reading = ser.readline().decode()
                is_reading = True
            except serial.SerialException as e:
                print("Disconnect of UART occured")
                ser.close()
                is_reading = False
                return None
            except:
                pass
            handle_data(reading)


def handle_data(data):
    global new_data_available
    global new_data
    global df
    new_data = {}
    try:
        new_data = json.loads(data)
        tim = datetime.now().strftime("%H:%M:%S.%f")
        print(new_data)
        new_data_available = True
        df_now = pd.DataFrame({
                'Time': [tim],
                'Sensor': [new_data['s']],
                'Value': [int(new_data['d'])]
                })
        df = df.append(df_now)
        df = df[-30:]

        if not new_data['s'] in registered_sensors:
            print("Added " + new_data['s'] + " to known sensors")
            registered_sensors.append(new_data['s'])

    except:
        print("Unrecognized format string, ignoring")



def start_monitoring(ser):
    global thread0
    global should_read
    should_read = True
    print("Starting reading")
    thread0 = threading.Thread(target=read_from_port, args=(ser,))
    thread0.start()

def stop_monitoring():
    global should_read
    global thread0
    print("Stopping reading")
    should_read = False


if __name__ == "__main__":
    main()
    