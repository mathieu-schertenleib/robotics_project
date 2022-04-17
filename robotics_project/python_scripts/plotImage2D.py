import numpy as np
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons
import serial
import struct
import sys
import signal
import time
from threading import Thread

# Can be converted into a portable package by using the PyInstaller module
# pip install pyinstaller (need to be used with Python3)
# cf. https://pyinstaller.readthedocs.io/en/v3.3.1/usage.html

image_subsampling = 4
image_width = 640 / image_subsampling
image_height = 120 / image_subsampling

# maximum value for an uint8
max_value = 255


# handler when closing the window
def handle_close(evt):
    # we stop the serial thread
    reader_thd.stop()


# update the plots
def update_plot():
    if reader_thd.need_to_update_plot():
        fig.canvas.draw_idle()
        reader_thd.plot_updated()


# function used to update the plot of the cam data
def update_cam_plot(port):
    cam_data = read_uint8_serial(port)

    if len(cam_data) > 0:
        plt.imshow(cam_data)

        reader_thd.tell_to_update_plot()


def rgb565_to_rgb(rgb565):
    r = (rgb565 & 0b1111_1000_0000_0000) >> 11
    g = (rgb565 & 0b0000_0111_1110_0000) >> 5
    b = (rgb565 & 0b0000_0000_0001_1111)
    return [r, g, b]


# reads the data in uint8 from the serial
def read_uint8_serial(port):
    state = 0

    while state != 5:

        # reads 1 byte
        c1 = port.read(1)
        # timeout condition
        if c1 == b'':
            print('Timeout...')
            return []

        if state == 0:
            if c1 == b'S':
                state = 1
            else:
                state = 0
        elif state == 1:
            if c1 == b'T':
                state = 2
            elif c1 == b'S':
                state = 1
            else:
                state = 0
        elif state == 2:
            if c1 == b'A':
                state = 3
            elif c1 == b'S':
                state = 1
            else:
                state = 0
        elif state == 3:
            if c1 == b'R':
                state = 4
            elif c1 == b'S':
                state = 1
            else:
                state = 0
        elif state == 4:
            if c1 == b'T':
                state = 5
            elif c1 == b'S':
                state = 1
            else:
                state = 0

    # reads the size
    # converts as short int in little endian the two bytes read
    size = struct.unpack('<h', port.read(2))
    # removes the second element which is void
    size = size[0]

    # reads the data
    rcv_buffer = port.read(size)
    data = []  # TODO: it might be way faster to preallocate

    # if we receive the good amount of data, we convert them in float32
    if len(rcv_buffer) == size:
        i = 0
        while i < size:
            rgb565 = struct.unpack_from('<h', rcv_buffer, i)
            rgb = rgb565_to_rgb(rgb565)
            data.append(rgb)
            i = i + 2

        print('Received !')
        return data
    else:
        print('Timeout...')
        return []


# thread used to control the communication part
class SerialThread(Thread):

    # init function called when the thread begins
    def __init__(self, port):
        Thread.__init__(self)
        self.contReceive = False
        self.alive = True
        self.need_to_update = False

        print('Connecting to port {}'.format(port))

        try:
            self.port = serial.Serial(port, timeout=0.5)
        except:
            print('Cannot connect to the e-puck2')
            sys.exit(0)

    # function called after the init
    def run(self):

        while self.alive:

            if self.contReceive:
                update_cam_plot(self.port)
            else:
                # flush the serial
                self.port.read(self.port.inWaiting())
                time.sleep(0.1)

    # enables the continuous reading
    def set_cont_receive(self, val):
        self.contReceive = True

    # disables the continuous reading
    def stop_reading(self, val):
        self.contReceive = False

    # tell the plot need to be updated
    def tell_to_update_plot(self):
        self.need_to_update = True

    # tell the plot has been updated
    def plot_updated(self):
        self.need_to_update = False

    # tell if the plot need to be updated
    def need_to_update_plot(self):
        return self.need_to_update

    # clean exit of the thread if we need to stop it
    def stop(self):
        self.alive = False
        self.join()
        if self.port.isOpen():
            while self.port.inWaiting() > 0:
                self.port.read(self.port.inWaiting())
                time.sleep(0.01)
            self.port.close()


# test if the serial port as been given as argument in the terminal
if len(sys.argv) == 1:
    print('Please give the serial port to use as argument')
    sys.exit(0)

# serial reader thread config
# begins the serial thread
reader_thd = SerialThread(sys.argv[1])
reader_thd.start()

# figure config
fig, ax = plt.subplots(num=None, figsize=(10, 8), dpi=80)
fig.canvas.set_window_title('CamReg plot')
plt.subplots_adjust(left=0.1, bottom=0.25)
fig.canvas.mpl_connect('close_event', handle_close)  # to detect when the window is closed and if we do a ctrl-c

# timer to update the plot from within the state machine of matplotlib
# because matplotlib is not thread safe...
timer = fig.canvas.new_timer(interval=50)
timer.add_callback(update_plot)
timer.start()

# positions of the buttons, sliders and radio buttons
colorAx = 'lightgoldenrodyellow'
receiveAx = plt.axes([0.4, 0.025, 0.1, 0.04])
stopAx = plt.axes([0.5, 0.025, 0.1, 0.04])

# config of the buttons, sliders and radio buttons
receiveButton = Button(receiveAx, 'Start reading', color=colorAx, hovercolor='0.975')
stop = Button(stopAx, 'Stop reading', color=colorAx, hovercolor='0.975')

# callback config of the buttons, sliders and radio buttons
receiveButton.on_clicked(reader_thd.set_cont_receive)
stop.on_clicked(reader_thd.stop_reading)

# starts the matplotlib main
plt.show()
