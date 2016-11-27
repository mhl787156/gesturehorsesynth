from gpiozero import DistanceSensor, Button
from psonic import *
from threading import Thread, Condition
import time
from dothat import backlight

import socket
import json


def doajson(j):
    if j:
        data = json.loads(j)
        height = data['positionz']/1000
        roll = data['roll']
        amp = .5 + (data['pitch'] + 20) / 40
        if -20 <= roll <= 20:
            synth = PIANO
        elif -20 > roll:
            synth = PULSE
        else:
            synth = PRETTY_BELL
        play_leap_note(height, amp, synth)
        print('leap note: ', height)

def json_listen():
    s = socket.socket()
    host = '169.254.108.151'
    port = 12345

    s.connect((host, port))
    try:
        json_ = ''
        while True:
            data = s.recv(1024).decode('utf-8')
            fragments = data.split('^')
            json_ += fragments[0]
            doajson(json_)

            for f in fragments[1:-1]:
                doajson(f)

            json_ = fragments[-1]
    finally:
        s.close()

class LiveLoop:
    loops = []
    running = []
    condition = Condition()

    def __init__(self, func, args):
        self.loops.append(self)
        self.thread = Thread(target=self.play)
        self.func = func
        self.args = args
        self.killed = False

    @classmethod
    def start_all(class_):
        for l in class_.loops:
            if l not in self.running:
                self.running.append(l)
                l.thread.start()

    @classmethod
    def kill_all(class_):
        for l in class_.loops:
            l.killed = True

    def start(self):
        self.killed = False
        self.running.append(self)
        self.thread.start()

    def play(self):
        while not self.killed:
            with self.condition:
                if self.running.index(self) != 0:
                    self.condition.wait()
                else:
                    self.condition.notifyAll()

            self.func(*self.args)
        self.running.remove(self)

SLEEPY_TIME = 1
is_recording = False
us_off = False
synth = BEEP
recording = []
threads = []
amp = 1.

pitch_sensor = DistanceSensor(echo=5, trigger=6)
amp_sensor = DistanceSensor(echo=13, trigger=19)
b_button = Button(26)
y_button = Button(9)
k_button = Button(7)
g_button = Button(10)

def play_note(pitch, amp, synth):
    asdf = scale(C4, LYDIAN)
    use_synth(synth)
    play(asdf[int(pitch*len(asdf))], release=.5, attack=.0, sustain=.5,
            amp=4*amp)
    sleep(SLEEPY_TIME)

def play_leap_note(pitch, amp, synth):
    use_synth(synth)
    asdf = scale(1, MIXOLYDIAN)
    pitch = pitch * 5
    note = C3 + 12 * int(pitch) + asdf[int((pitch - int(pitch)) * len(asdf))]
    play(note, release=.1, attack=.0, sustain=.1, amp=10*amp)
    sleep(SLEEPY_TIME/2)

def b_button_func():
    global synth
    synths = [BEEP, PLUCK, PROPHET, PULSE]
    current = 0
    while True:
        b_button.wait_for_press()
        current = (current + 1) % len(synths)
        synth = synths[current]
        time.sleep(.3)

def y_button_func():
    global is_recording
    global recording
    while True:
        y_button.wait_for_press()
        is_recording = True
        backlight.hue(1)
        time.sleep(.3)
        y_button.wait_for_press()
        is_recording = False
        backlight.hue(0)
        print('start recording playback: ',recording)
        loop = LiveLoop(play_recording, (recording,))
        loop.start()
        recording = []
        time.sleep(.3)

def k_button_func():
    while True:
        k_button.wait_for_press()
        LiveLoop.kill_all()
        print('kill all loops')
        time.sleep(.3)

def g_button_func():
    global us_off
    while True:
        g_button.wait_for_press()
        us_off = not us_off
        print('us off? ',us_off)
        time.sleep(.3)

def play_recording(notes):
    global amp
    for p,s in notes:
        play_note(p,amp,s)
        time.sleep(SLEEPY_TIME)


Thread(target=b_button_func).start()
Thread(target=y_button_func).start()
Thread(target=k_button_func).start()
Thread(target=g_button_func).start()
Thread(target=json_listen).start()

print("I'm a good boy.")
pitch = .5
try:
    while True:
        if not us_off:
            pitch_ = pitch_sensor.distance
            if .01 < pitch_ < .8:
                pitch = pitch_ / .8
                print(pitch)
                if is_recording:
                    recording.append((pitch, synth))
                else:
                    backlight.hue(pitch)
                play_note(pitch, amp, synth)

            #amp_ = amp_sensor.distance
            #if .1 < amp_ < .9:
            #    amp = amp_


except KeyboardInterrupt:
    LiveLoop.kill_all()

