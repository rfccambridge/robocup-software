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
import sys
sys.path.append('..')
from johnrobot import JohnRobot
import pygame
import time

print('Connecting to robot...')
robot = JohnRobot()
print('Connected to robot.')

SPEED = 200 
ROTATION_SPEED = 130
COMMAND_TTL = 0.3
COMMAND_DELAY = 0.15
DRIBBLER_SPEED_INCREMENT = 20
dribbler_speed = 255

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
    # Button mapping
    # 0 - X   1 - A    2 - B   
    # 3 - Y   4 - Lb    5 - Rb   
    button_x = js.get_button(0)
    button_a = js.get_button(1)
    button_b = js.get_button(2)
    button_y = js.get_button(3)
    button_lb = js.get_button(4)
    button_rb = js.get_button(5)
    speed_x, speed_y = a * SPEED, b * SPEED
    print("Going with vector ({},{})".format(speed_x, speed_y))

    if button_lb:
        dribbler_speed = max(dribbler_speed - DRIBBLER_SPEED_INCREMENT, 0)
        robot.dribble(dribbler_speed)
        continue

    if button_rb:
        dribbler_speed = min(dribbler_speed + DRIBBLER_SPEED_INCREMENT, 255)
        robot.dribble(dribbler_speed)
        continue

    if button_y:
        robot.kill()
        print("KILL KILL KILL")
        continue

    robot.move(SPEED * a, SPEED * b, 0, COMMAND_TTL)

