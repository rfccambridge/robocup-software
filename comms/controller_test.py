"""Quick test script that moves the robot using the Game Controller.
If you get a PermissionError, add the current user to the input group.
    sudo usermod -a -G input robocup
Then, log out and log back in to make sure the permissions have refreshed.

GAME CONTROLLER INFO:
Axis0 and 1 are right and down respectively on LEFT joystick
ranges from -1 to 1
Axis 2 and 3 are right and down respectively on RIGHT joystick
ranges from -1 to 1
0 is always the neutral position
"""
import pygame
import time
try:
    from radio import Radio
    from robot_commands import RobotCommands
except (SystemError, ImportError):
    from .radio import Radio
    from .robot_commands import RobotCommands

print('Setting up radio connection...')
radio = Radio()
print('Radio Connected.')

# TODO: Standardize with constants in robot_commands?
MAX_XY_SPEED = 600  # mm/s
MAX_ROTATION_SPEED = 6.2  # robot radians/s

pygame.joystick.init()
pygame.display.init()
pygame.joystick.Joystick(0).init()
print('Name of Joystick:')
js = pygame.joystick.Joystick(0)
print(js.get_name())

# set up commands robot for a single robot
ROBOT_ID = 8
robot_commands = RobotCommands()

while True:
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
    button_lt = js.get_button(6)
    button_rt = js.get_button(7)
    speed_lateral, speed_forward = a * MAX_XY_SPEED, -b * MAX_XY_SPEED
    speed_rotation = -c * MAX_ROTATION_SPEED
    robot_commands.set_speeds(speed_lateral, speed_forward, speed_rotation)
    robot_commands.set_speeds(speed_lateral, speed_forward, speed_rotation)

    if button_lt:
        print("Stopping Dribble")
        robot_commands.is_dribbling = False
    if button_rt:
        print("Starting Dribble")
        robot_commands.is_dribbling = True

    if button_lb:
        robot_commands.is_charging = True
    else:
        robot_commands.is_charging = False

    if button_rb:
        robot_commands.is_kicking = True
    else:
        robot_commands.is_kicking = False

    # print(robot_commands)
    info = radio.read()
    if info is not None:
        print(info)

    # send serialized message for whole team (just 1 robot)
    team_commands = {ROBOT_ID: robot_commands}
    message = RobotCommands.get_serialized_team_command(team_commands)
    radio.send(message)
    # yield to other threads - loop only as fast as radio can send
    time.sleep(Radio.MESSAGE_DELAY)
