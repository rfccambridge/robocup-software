import threading
import time
import math
import numpy as np
from .robot import Robot


# default proportional scaling constant for distance differences
SPEED_SCALE = .8
DEFAULT_MAX_SPEED = 700
DEFAULT_MIN_SPEED = 50
# TODO: make rotation actually work
ROTATION_SPEED_SCALE = 0

# how long a command can be run without being updated
COMMAND_DURATION = .2


class Comms(object):
    """Comms class spins a thread to repeated send the commands stored in
       gamestate to the robots via radio"""
    # TODO: when we get multiple comms, connect to all robots that are available
    def __init__(self, gamestate):
        self._gamestate = gamestate
        self._robots = dict() # dict from id to robot (comms class)
        # store previously sent commands to reduce redundant commands
        self._robot_dribblers = dict()  # Dict of previously sent dribbler speeds for robot_id
        self._robot_chargings = dict()  # Dict of previously sent kicker chargings for robot_id
        
        self._is_sending = False
        self._thread = None
        self._last_sent_time = None

    def die(self):
        for robot in self._robots:
            robot.die()

    def start_sending(self):
        for robot_id in self._gamestate.get_robot_ids('blue'):
            self._robots[robot_id] = Robot()
        
        self._is_sending = True
        self._thread = threading.Thread(target=self.sending_loop)
        # set to daemon mode so it will be easily killed
        self._thread.daemon = True
        self._thread.start()
        
    def sending_loop(self):
        while self._is_sending:
            for robot_id in self._gamestate.get_robot_ids('blue'):
                robot_commands = self._gamestate.get_robot_commands('blue', robot_id)
                waypoints = robot_commands.waypoints
                if robot_id not in self._robots:
                    print("Commanding a Robot that was not connected when initializing")
                    print("(not seen by vision) - trying to connect now...")
                    self._robots[robot_id] = Robot()
                    
                robot = self._robots[robot_id]

                pos = self._gamestate.get_robot_position(robot_id, 'blue')
                # stop the robot if we've lost track of it
                if self._gamestate.is_robot_lost(robot_id):
                    robot.move(0, 0, 0, COMMAND_DURATION)
                    continue
                og_x, og_y, og_w = pos
                # if close enough to first waypoint, delete and move to next one
                while len(waypoints) > 1 and self.close_enough(pos, waypoints[0]):
                    waypoints.pop(0)
                goal_pos, min_speed, max_speed = waypoints[0]
                goal_x, goal_y, goal_w = goal_pos
                if min_speed is None:
                    min_speed = DEFAULT_MIN_SPEED
                if max_speed is None:
                    max_speed = DEFAULT_MAX_SPEED
                delta = (goal_x - og_x, goal_y - og_y)
                # normalized offsets from robot's perspective
                norm_x, norm_y = self.normalize(og_w, delta)
                norm_w = self.trim_angle(goal_w - og_w)

                #print("dx: {}, dy: {}, dw: {}".format(norm_x, norm_y, norm_w))
                
                # move with speed proportional to delta
                linear_speed = self.magnitude(delta) * SPEED_SCALE
                linear_speed = min(min_speed + linear_speed, max_speed)
                robot.move(linear_speed * norm_x,
                           linear_speed * norm_y,
                           norm_w * ROTATION_SPEED_SCALE,
                           COMMAND_DURATION)

                # send dribbler commands
                dribbler_speed = robot_commands.dribbler
                if dribbler_speed != self._robot_dribblers[robot_id]:
                    self._robot_dribblers[robot_id] = dribbler_speed
                    robot.dribble(dribbler_speed)

                # TODO: send other commands for dribbler and kicking
            if self._last_sent_time is not None:
                delta = time.time() - self._last_sent_time
                if delta > .3:
                    print("Comms loop unexpectedly large delay: " + str(delta))
            self._last_sent_time = time.time()
            # yield to other threads - run this loop at most 20 times per second
            time.sleep(.05)

    # used for eliminating intermediate waypoints
    def close_enough(self, current, goal):
        cx, cy, cw = current
        gx, gy, gw = current
        dx, dy, dw = abs(cx - gx), abs(cy - gy), abs(cw - gw)
        # for now ignoring rotation
        DISTANCE_THRESHOLD = 10
        return (dx + dy) ** .5 < DISTANCE_THRESHOLD

    def stop_sending(self):
        self._is_sending = False
        self._thread.join()
        self._thread = None

    # coordinate math helper functions
    def normalize(self, w_robot, vector):
        """Transforms real world x, y vector into a normalized vector in the
        reference frame of the robot"""
        assert(len(vector) == 2)
        if vector == (0, 0):
            return vector
        x, y = vector
        w_rot = w_robot - np.arctan2(y, x)
        return (np.sin(w_rot), np.cos(w_rot))

    def magnitude(self, v):
        x, y = v
        return (x**2 + y**2) ** .5

    def trim_angle(self, angle):
        """Transforms an angle into the range -pi to pi, for shortest turning"""
        while angle > 2 * math.pi:
            angle -= 2 * math.pi
        while angle < -1 * math.pi:
            angle += 2 * math.pi
        if angle > math.pi:
            angle -= 2 * math.pi
        if angle < -math.pi:
            angle += 2 * math.pi
        return angle
