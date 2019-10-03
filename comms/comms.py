import threading
import time
from .robot import Robot
from .transform import RealWorldCoordTransformer

# default proportional scaling constant for distance differences
SPEED_SCALE = .35
MAX_SPEED = 150
# how long a command can be run without being updated
COMMAND_DURATION = .2



class Comms(object):
    """Comms class spins a thread to repeated send the commands stored in
       gamestate to the robots via radio"""
    # TODO: when we get multiple comms, connect to all robots that are available
    def __init__(self, gamestate):
        self._gamestate = gamestate
        self._robots = dict() # dict from id to robot (comms class)
        self._is_sending = False
        self._thread = None
        # TODO: why is this a class? can we move to a shared utilities folder? - Kendall
        self._trans = RealWorldCoordTransformer()
        self._last_sent_time = None

    def die(self):
        for robot in self._robots:
            robot.die()

    def start_sending(self):
        self._is_sending = True
        self._thread = threading.Thread(target=self.sending_loop)
        self._thread.start()

    def sending_loop(self):
        while self._is_sending:
            for robot_id, waypoints in self._gamestate.robot_waypoints.items():
                # TODO: should connect in the beginning? (i.e. have a preset list of IDs)
                if robot_id not in self._robots:
                    self._robots[robot_id] = Robot()
                # TODO: if close enough to first waypoint, delete and move to next one
                robot = self._robots[robot_id]

                pos = self._gamestate.get_robot_position(robot_id)
                # stop the robot if we've lost track of it
                if self._gamestate.is_robot_lost(robot_id):
                    robot.move(0, 0, 0, COMMAND_DURATION)
                    continue
                og_x, og_y, og_w = pos
                goal_x, goal_y = waypoints[0]
                delta = (goal_x - og_x, goal_y - og_y)
                # normalized offsets from robot's perspective
                robot_x, robot_y = self._trans.transform(og_w, delta)
                if False:
                    print("Original coordinates", og_x, og_y, og_w)
                    print('Delta {}'.format(delta))
                    print('(normalized diff) Robot X %f Robot Y %f' % (robot_x, robot_y))

                # move with speed proportional to delta
                speed = min(self._trans.magnitude(delta) * SPEED_SCALE, MAX_SPEED)
                robot.move(speed * robot_y, speed * robot_x, 0, COMMAND_DURATION)

                # TODO: send other commands for dribbler and kicking
            if self._last_sent_time is not None:
                delta = time.time() - self._last_sent_time
                if delta > .3:
                    print("Comms loop unexpectedly large delay: " + str(delta))
            self._last_sent_time = time.time()
            # yield to other threads - run this loop at most 20 times per second
            time.sleep(.05)

    def stop_sending(self):
        self._is_sending = False
        self._thread.join()
        self._thread = None
