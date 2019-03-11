"""Quick test script that moves the robot using the Game Controller. If you get a
PermissionError, you will need to add the current user to the input group.
    sudo usermod -a -G input robocup
Then, log out and log back in to make sure the permissions have refreshed.

GAME CONTROLLER INFO:
Axis0 and 1 are right and down respectively on LEFT joystick
ranges from -1 to 1
Axis 2 and 3 are right and down respectively on RIGHT joystick
ranges from -1 to 1
0 is always the neutral position
"""
from comms import JohnRobot
import pygame
import time

print('Connecting to robot...')
robot = JohnRobot()
print('Connected to robot.')

SPEED = 60
ROTATION_SPEED = 60
COMMAND_TTL = 0.2
COMMAND_DELAY = 0.1

last_command_sent = time.time()

pygame.joystick.init()
pygame.display.init()
pygame.joystick.Joystick(0).init()
print('Name of Joystick:')
js = pygame.joystick.Joystick(0)
print(js.get_name())


while True:
    # Need to limit the number of commands sent per second,
    # or the XBEE will get overloaded and drop packets.
    if time.time() - last_command_sent < COMMAND_DELAY:
        continue
    
    last_command_sent = time.time()
    pygame.event.pump()
    a = js.get_axis(0)
    b = js.get_axis(1)
    c = js.get_axis(2)
    d = js.get_axis(3)
    speed_x, speed_y = a * SPEED, b * SPEED
    print("Going with vector ({},{})".format(speed_x, speed_y))


    robot.move(SPEED * a, SPEED*b, 0, COMMAND_TTL)

