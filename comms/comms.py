import threading
import time
import math
import numpy as np
from collections import deque
from .robot import Robot
from .omni import OmniComms


# default proportional scaling constant for distance differences
SPEED_SCALE = .8
# Max speed from max power to motors => [free-spinning] 1090 mm/s (see firmware)
# Reduce that by multiplying by min(sin(theta), cos(theta)) of wheels
# Goal is to get upper bound on we can send and expect firmware to obey accurately
DEFAULT_MAX_SPEED = 650 # pretty conservative, maybe we can be more aggressive?
DEFAULT_MIN_SPEED = 50
# TODO: make rotation actually work
ROTATION_SPEED_SCALE = 0

# how long a command can be run without being updated
COMMAND_DURATION = .2
# limiting throughput of messages sent to robot
COMMAND_DELAY = .15
CMD_MOVE = 0
CMD_DRIBBLE = 1
CMD_KILL = 2


class Comms(object):
    """Comms class spins a thread to repeated send the commands stored in
       gamestate to the robots via radio"""
    # TODO: when we get multiple comms, connect to all robots that are available
    def __init__(self, gamestate, team):
        self._gamestate = gamestate
        assert(team in ['blue', 'yellow'])
        self._team = team

        self._comms = OmniComms()

        # store previously sent commands to reduce redundant commands
        self._robot_dribblers = dict()  # Dict of previously sent dribbler speeds for robot_id
        self._robot_chargings = dict()  # Dict of previously sent kicker chargings for robot_id
        self._robot_last_command_times = dict()
        
        self._is_sending = False
        self._sending_thread = None
        self._last_send_loop_time = None

        self._is_receiving = False
        self._receiving_thread = None
        self._messages_received = []
        self._last_receive_loop_time = None


    def die(self):
        self._comms.close()

    def start_sending(self):
        self._is_sending = True
        self._sending_thread = threading.Thread(target=self.sending_loop)
        # set to daemon mode so it will be easily killed
        self._sending_thread.daemon = True
        self._sending_thread.start()

    def start_receiving(self):
        self._is_receiving = True
        self._receiving_thread = threading.Thread(target=self.receiving_loop)
        # set to daemon mode so it will be easily killed
        self._receiving_thread.daemon = True
        self._receiving_thread.start()        
        
    def sending_loop(self):
        while self._is_sending:
            for robot_id in self._gamestate.get_robot_ids(self._team):
                robot_commands = self._gamestate.get_robot_commands(self._team, robot_id)
                waypoints = robot_commands.waypoints

                pos = self._gamestate.get_robot_position(self._team, robot_id)
                # stop the robot if we've lost track of it
                if self._gamestate.is_robot_lost(self._team, robot_id):
                    self.move_command(robot_id, 0, 0, 0, COMMAND_DURATION)
                    continue
                og_x, og_y, og_w = pos
                # if close enough to first waypoint, delete and move to next one
                if waypoints:
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
                    self.move_command(
                        robot_id,
                        linear_speed * norm_x,
                        linear_speed * norm_y,
                        norm_w * ROTATION_SPEED_SCALE,
                        COMMAND_DURATION)

                # send dribbler commands
                dribbler_speed = robot_commands.dribbler_speed
                self.dribble_command(robot_id, dribbler_speed)                    

                # TODO: send other commands for dribbler and kicking
            if self._last_send_loop_time is not None:
                delta = time.time() - self._last_send_loop_time
                if delta > .3:
                    print("Comms sending loop unexpectedly large delay: " + str(delta))
            self._last_send_loop_time = time.time()
            # yield to other threads - run this loop at most 20 times per second
            # Warning - looping too fast might overload throttle, so some commands never sent
            time.sleep(.05)

    def receiving_loop(self):
        while self._is_receiving:
            # TODO: save messages for log
            print(self._comms.read())
            # TODO: update relevant data into gamestate
            if self._last_receive_loop_time is not None:
                delta = time.time() - self._last_receive_loop_time
                if delta > .3:
                    print("Comms receiving loop unexpectedly large delay: " + str(delta))
            self._last_receive_loop_time = time.time()
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

    def stop_sending_and_receiving(self):
        if self._is_sending:
            self._is_sending = False
            self._sending_thread.join()
            self._sending_thread = None
        if self._is_receiving:
            self._is_receiving = False
            self._receiving_thread.join()
            self._receiving_thread = None
        self.die()

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

    # COMMAND FUNCTIONS - not guaranteed to send (can repeatedly call in a loop)
    # sends command if throttle conditions are met, returns whether command was sent
    def try_send_command(self, robot_id, command_string):
        if robot_id not in self._robot_last_command_times:
            can_send = True
        else:
            last_time = self._robot_last_command_times[robot_id]
            can_send = time.time() - last_time > COMMAND_DELAY
        if can_send:
            self._comms.send(command_string)
            self._robot_last_command_times[robot_id] = time.time()
        return can_send

    def kill_command(self):
        # TODO: where is this used? ever for single robot?
        # Use robot_id = -1 to broadcast to all robots
        robot_id = -1
        cmd = "{},{}".format(robot_id, CMD_KILL)
        # for now, kill bypasses throughput restrictions
        self._comms.send(cmd)

    def move_command(self, robot_id, x, y, w, ttl=0.5):
        """Move x, y, and rotation velocity - x, y are mm/s, 
           and y is radians/s of the robot"""
        robot_id = -1 # TODO delete
        time_ms = int(ttl * 1000.0)
        cmd = "{},{},{},{},{},{}".format(robot_id, CMD_MOVE, x, y, w, time_ms)
        self.try_send_command(robot_id, cmd)

    def dribble_command(self, robot_id, dribbler_speed):
        # only send command if its a change in speed
        if dribbler_speed != self._robot_dribblers.get(robot_id, None):
            cmd = "{},{},{}".format(robot_id, CMD_DRIBBLE, dribbler_speed)
            if self.try_send_command(robot_id, cmd) and robot_id != -1:
                self._robot_dribblers[robot_id] = dribbler_speed

    def kick_command(self, robot_id):
        raise NotImplementedError

    def charge_command(self, robot_id):
        """IMMA CHARGIN MY KICKER!!!!!"""
        raise NotImplementedError

