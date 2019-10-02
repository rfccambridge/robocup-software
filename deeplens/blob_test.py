# You should use python3 for compatibility with xbee.
import cv2
import numpy as np
import imutils
from collections import deque
import sys

sys.path.append('/home/aws_cam/robocup-test/comms')

from johnrobot import JohnRobot

print('Connecting to robot')
robot = JohnRobot()
print('Connected to robot')

# Wiggle the robot a little so we know we have started
for _ in range(10):
    robot.move(0, 40, 0)
for _ in range(10):
    robot.move(0, -40, 0)

cap = cv2.VideoCapture("/opt/awscam/out/ch2_out.mjpeg")
pts = deque(maxlen=10)

def detect_ball(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Filter for green
    lower = (29, 86, 80)
    upper = (64, 255, 255)
    mask = cv2.inRange(hsv, lower, upper)
    # mask = cv2.erode(mask, None, iterations=2)
    # mask = cv2.dilate(mask, None, iterations=2)
    
    # find contours in the mask and initialize the current
    # (x, y) center of the ball
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    center = None
 
    # only proceed if at least one contour was found
    if len(cnts) > 0:
        # find the largest contour in the mask, then use
        # it to compute the minimum enclosing circle and
        # centroid
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        M = cv2.moments(c)
        try:
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
        except ZeroDivisionError:
            return None

        # only proceed if the radius meets a minimum size
        if radius > 3:
            # draw the circle and centroid on the frame,
            # then update the list of tracked points
            return center, radius
        else:
            return None
    else:
        return None

for _ in range(200):
    success, frame = cap.read()
    if not success:
        raise RuntimeError('Failed to get new frame from camera')
    frame = cv2.resize(frame, (640, 480))
    frame = np.rot90(frame)
    h, w, _ = frame.shape
    
    balls = detect_ball(frame)
    if balls:
        center, radius = balls
        if radius < 6:
            robot.move(0, 0, 0)
        elif radius > 100:
            robot.move(0, 0, 0)
        else:
            # cv2.circle(frame, center, int(radius), (0, 255, 255), 2)
            # cv2.circle(frame, center, 5, (0, 0, 255), -1)
            width, height = center
            pixel_diff = (width - w / 2.0)
            strength = 20.0
            rotate = strength * pixel_diff / w
            print('rotating with strength %d' % rotate)
            robot.move(20, 0, rotate)
	
            pts.appendleft(center)
            print('Ball detected at (%d, %d) with size %d: ' % (center[0], center[1], radius))
    else:
       robot.move(0, 0, 0)
 
    # update the points queue
    # cv2.imshow("output", frame)
    # cv2.waitKey(1)

robot.die()