################################################################################
# Copyright (C) 2012-2013 Leap Motion, Inc. All rights reserved.               #
# Leap Motion proprietary and confidential. Not for distribution.              #
# Use subject to the terms of the Leap Motion SDK Agreement available at       #
# https://developer.leapmotion.com/sdk_agreement, or another agreement         #
# between Leap Motion and you, your company or other organization.             #
################################################################################

import socket
import time
import json
import Leap, sys, thread, time
from Leap import CircleGesture, KeyTapGesture, ScreenTapGesture, SwipeGesture

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = '169.254.108.151'
port = 12345
connections = []
s.bind((host, port))


class SocketListener(Leap.Listener):
    state_names = ['STATE_INVALID', 'STATE_START', 'STATE_UPDATE', 'STATE_END']

    def __init__(self, s):
        super(SocketListener, self).__init__()
        self.s = s
        self.sendframe = 50
        self.counter = 0
    
    def senddata(self, data):
        print data
        self.counter = (self.counter + 1) % self.sendframe
        if self.counter % self.sendframe == 0:
            jsondata = json.dumps(data)
            print jsondata
            map(lambda c: c.send('^'), connections)
            map(lambda c: c.send(jsondata), connections)

    def on_init(self, controller):
        print "Initialized"

    def on_connect(self, controller):
        print "Connected"

        # Enable gestures
        controller.enable_gesture(Leap.Gesture.TYPE_CIRCLE);
        controller.enable_gesture(Leap.Gesture.TYPE_KEY_TAP);
        controller.enable_gesture(Leap.Gesture.TYPE_SCREEN_TAP);
        controller.enable_gesture(Leap.Gesture.TYPE_SWIPE);

    def on_disconnect(self, controller):
        # Note: not dispatched when running in a debugger.
        print "Disconnected"

    def on_exit(self, controller):
        print "Exited"

    def on_frame(self, controller):
        # Get the most recent frame and report some basic information
        frame = controller.frame()

        data = {"frame _id" : frame.id,
                "timestamp" : frame.timestamp}
            
        sdata = {"timestamp" : frame.timestamp}
        
        # Get hands
        handslist = []
        shandslist = []
        for hand in frame.hands:

            handType = "left_hand" if hand.is_left else "right_hand"

            handdata = {"type" : handType,
                        "id" : hand.id,
                        "position" : hand.palm_position.to_tuple()}
            
            shanddata = {}
            # print hand.palm_position.to_tuple()
            _, shanddata['positionz'], _ = hand.palm_position.to_tuple()

            # Get the hand's normal vector and direction
            normal = hand.palm_normal
            direction = hand.direction

            # Calculate the hand's pitch, roll, and yaw angles
            # print "  pitch: %f degrees, roll: %f degrees, yaw: %f degrees" % (
            #     direction.pitch * Leap.RAD_TO_DEG,
            #     normal.roll * Leap.RAD_TO_DEG,
            #     direction.yaw * Leap.RAD_TO_DEG)
            
            shanddata['pitch'] = handdata['pitch'] = direction.pitch * Leap.RAD_TO_DEG
            shanddata['roll'] = handdata['roll'] = normal.roll * Leap.RAD_TO_DEG
            handdata['yaw'] = direction.yaw * Leap.RAD_TO_DEG

            handslist.append(handdata)
            shandslist.append(shanddata)
        
        data['hands'] = handslist
        # sdata['hands'] = shandslist
        if len(shandslist) != 0:
            sdata['positionz'] = shandslist[0]['positionz']
            sdata['pitch'] = shandslist[0]['pitch']
            sdata['roll'] = shandslist[0]['roll']

        # Get tools
        toolslist = []
        for tool in frame.tools:
            toolslist.append({
                'id' : tool.id,
                'tip_position' : tool.tip_position,
                'direction' : tool.direction
            })
            print "  Tool id: %d, position: %s, direction: %s" % (
                tool.id, tool.tip_position, tool.direction)
        data['tools'] = toolslist

        # Get gestures
        gesturelist = []
        for gesture in frame.gestures():

            #Circle Gesture
            if gesture.type == Leap.Gesture.TYPE_CIRCLE:
                circle = CircleGesture(gesture)

                # Determine clock direction using the angle between the pointable and the circle normal
                if circle.pointable.direction.angle_to(circle.normal) <= Leap.PI/2:
                    clockwiseness = "clockwise"
                else:
                    clockwiseness = "counterclockwise"

                # Calculate the angle swept since the last frame
                swept_angle = 0
                if circle.state != Leap.Gesture.STATE_START:
                    previous_update = CircleGesture(controller.frame(1).gesture(circle.id))
                    swept_angle =  (circle.progress - previous_update.progress) * 2 * Leap.PI
                
                gesturelist.append({
                    'gesture' : 'circle',
                    'id' : gesture.id,
                    'radius' : circle.radius,
                    'angle' : swept_angle * Leap.RAD_TO_DEG,
                    'degrees' : clockwiseness
                })
                # print "  Circle id: %d, %s, progress: %f, radius: %f, angle: %f degrees, %s" % (
                #         gesture.id, self.state_names[gesture.state],
                #         circle.progress, circle.radius, swept_angle * Leap.RAD_TO_DEG, clockwiseness)
            
            #Swipe Gesture
            if gesture.type == Leap.Gesture.TYPE_SWIPE:
                swipe = SwipeGesture(gesture)
                # print "  Swipe id: %d, state: %s, position: %s, direction: %s, speed: %f" % (
                #         gesture.id, self.state_names[gesture.state],
                #         swipe.position, swipe.direction, swipe.speed)

                gesturelist.append({
                    'gesture' : 'swipe',
                    'id' : gesture.id,
                    'position' : swipe.position.to_tuple(),
                    'direction' : swipe.direction.to_tuple(),
                    'speed' : swipe.speed
                })

        # sdata["gestures"] = data["gestures"] = gesturelist

        
        if not (frame.hands.is_empty and frame.gestures().is_empty):
            # self.senddata(data)
            self.senddata(sdata)            
            # print ""
            

    def state_string(self, state):
        if state == Leap.Gesture.STATE_START:
            return "STATE_START"

        if state == Leap.Gesture.STATE_UPDATE:
            return "STATE_UPDATE"

        if state == Leap.Gesture.STATE_STOP:
            return "STATE_STOP"

        if state == Leap.Gesture.STATE_INVALID:
            return "STATE_INVALID"

def main():
    
    # Create a sample listener and controller
    listener = SocketListener(s)
    controller = Leap.Controller()

    # Have the sample listener receive events from the controller
    controller.add_listener(listener)

    # Keep this process running until Enter is pressed
    print "Press Enter to quit..."
    try:
        s.listen(5)
        while len(connections) < 1:
            c, addr = s.accept()
            print ('Got connection from', addr)
            # c.send('Now Connected to Leap Motion')
            connections.append(c)

        sys.stdin.readline()
    except KeyboardInterrupt:
        quit()
    finally:
        # Remove the sample listener when done
        controller.remove_listener(listener)
        map(lambda c: c.close() , connections)


if __name__ == "__main__":
    main()
