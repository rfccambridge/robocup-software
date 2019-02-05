"""Quick test script that moves the robot using the keyboard. If you get a
PermissionError, you will need to add the current user to the input group.
    sudo usermod -a -G input robocup
Then, log out and log back in to make sure the permissions have refreshed."""
import inputs
from comms import JohnRobot
import time

print('Connecting to robot...')
robot = JohnRobot()
print('Connected to robot.')

SPEED = 30
ROTATION_SPEED = 15
COMMAND_TTL = 0.2
COMMAND_DELAY = 0.1

last_command_sent = time.time()

while True:
    # Need to limit the number of commands sent per second,
    # or the XBEE will get overloaded and drop packets.
    if time.time() - last_command_sent < COMMAND_DELAY:
        continue
    
    last_command_sent = time.time()
    events = inputs.get_key()
    for event in events:
        if event.code == "KEY_W":
            robot.move(SPEED, 0, 0, time=COMMAND_TTL)
        elif event.code == "KEY_A":
            robot.move(0, -SPEED, 0, time=COMMAND_TTL)
        elif event.code == "KEY_S":
            robot.move(-SPEED, 0, 0, time=COMMAND_TTL)
        elif event.code == "KEY_D":
            robot.move(0, SPEED, 0, time=COMMAND_TTL)
        elif event.code == "KEY_Q":
            robot.move(0, 0, -ROTATION_SPEED, time=COMMAND_TTL)
        elif event.code == "KEY_E":
            robot.move(0, 0, ROTATION_SPEED, time=COMMAND_TTL)
        else:
            pass
