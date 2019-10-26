try:
    from .omni import OmniComms
except SystemError:
    from omni import OmniComms
import numpy as np
import time
import threading

CMD_MOVE = 0
CMD_DRIBBLE = 1
CMD_KILL = 2

class Robot(object):
    """Class that controls a robot - contains basic logic for moving to a point, 
    but mostly just interfaces with firmware through xbee radio"""
    def __init__(self, command_delay=0.15):
        self.comms = OmniComms()
        self.last_command_time = time.time()
        self.last_command_delay = command_delay

    def kill(self):
        robot_id = -1
        cmd = "{},{}".format(robot_id, CMD_KILL)
        self.comms.send(cmd)

    def move(self, x, y, w, ttl=0.5):
        """Move x, y, and rotation velocity. x, y are mm/s, 
           and y is radians/s of the robot"""
        # Use -1 as first element to broadcast to all robots
        if time.time() - self.last_command_time > self.last_command_delay:
            self.last_command_time = time.time()
            robot_id = -1
            time_ms = int(ttl * 1000.0)
            cmd = "{},{},{},{},{},{}".format(robot_id, CMD_MOVE, x, y, w, time_ms)
            self.comms.send(cmd)

    def dribble(self, power):
        # Use -1 as first element to broadcast to all robots
        if time.time() - self.last_command_time > self.last_command_delay:
            self.last_command_time = time.time()
            robot_id = -1
            cmd = "{},{},{}".format(robot_id, CMD_DRIBBLE, power)
            self.comms.send(cmd)

    def kick(self):
        raise NotImplementedError

    def charge(self):
        """IMMA CHARGIN MY KICKER!!!!!"""
        raise NotImplementedError

    def die(self):
        self.comms.close()


if __name__ == '__main__':
    test = Robot()
    for _ in range(3):
        test.move(30, 0, 0, time=1.0)
        time.sleep(0.9)
        test.move(0, 30, 0, time=1.0)
        time.sleep(0.9)
        test.move(-30, 0, 0, time=1.0)
        time.sleep(0.9)
        test.move(0, -30, 0, time=1.0)
        time.sleep(0.9)
    test.die()
