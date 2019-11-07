import math
import numpy as np

# TODO: move serialization into separate file?
# serialization constants - must match with firmware
MIN_X = -1000
MAX_X = 1000
MIN_Y = -1000
MAX_Y = 1000
MIN_W = -2 * math.pi
MAX_W = 2 * math.pi
# range of values allowed to appear in the serialized message bits
# even to avoid rounding 0, < END_KEY so nothing gets encoded to END_KEY
MAX_ENCODING = 254
# Single-byte key to ensure that xbee message is not corrupted.
START_KEY = bytes([100])
# Single-byte Key to terminate messages - MUST NEVER APPEAR IN MESSAGE BODY
END_KEY = bytes([255])
# For padding multi-commands - 15 should be higher than any valid robot_id
EMPTY_COMMAND = bytearray([15, 0, 0, 0])
# Length of serialized commands for single robot
SINGLE_ROBOT_COMMAND_LENGTH = 4
# Length of final message to be sent to firmware
# (contains 6 robots commands, plus a start key and end key)
TEAM_COMMAND_MESSAGE_LENGTH = 26

"""
Contains information about a robot's command state. Provides functions for
deriving lower level commands from high level (i.e. waypoints => (x, y, w))
Also specifies message serialization to interface with firmware.
"""


class RobotCommands:
    # constants for deriving speed from waypoints TODO: obselete?
    # default proportional scaling constant for distance differences
    SPEED_SCALE = .8
    # Max speed from max power to motors => [no-load] 1090 mm/s (see firmware)
    # Reduce that by multiplying by min(sin(theta), cos(theta)) of wheels
    # Goal is to get upper bound on what firmware can obey accurately
    DEFAULT_MAX_SPEED = 650  # maybe we can be more aggressive?
    DEFAULT_MIN_SPEED = 0
    # TODO: make rotation actually work
    ROTATION_SPEED_SCALE = 0

    def __init__(self):
        # each waypoint is (pos, speed)?
        self.waypoints = []
        # (private) speed values from robot's perspective
        self._x = 0  # speed x mm/s
        self._y = 0  # speed y mm/s
        self._w = 0  # speed robot radians/s
        # other commands - TODO: create interfaces i.e. charge_until?
        self.is_dribbling = False
        self.is_charging = False
        self.is_kicking = False

    # returns serialized commands for single robot in 4 bytes
    def get_serialized_command(self, robot_id):
        if not MIN_X < self._x < MAX_X:
            raise ValueError("x={} is too big".format(self._x))
        if not MIN_Y < self._y < MAX_Y:
            raise ValueError("y={} is too big".format(self._y))
        if not MIN_W < self._w < MAX_W:
            raise ValueError("w={} is too big".format(self._w))
        if robot_id < 0 or robot_id > 14:
            raise ValueError("robot_id={} is too big".format(robot_id))

        # pack robot_id and boolean commands into the first byte
        first_byte = 0
        first_byte = first_byte | (15 & robot_id)  # 4 least significant bits
        first_byte = first_byte | int(self.is_dribbling) << 5  # Bit 5
        first_byte = first_byte | int(self.is_charging) << 6  # Bit 6
        first_byte = first_byte | int(self.is_kicking) << 7  # Bit 7

        # pack x, y, w each into a byte (reduces granularity)
        x_byte = int(((self._x - MIN_X) / (MAX_X - MIN_X)) * MAX_ENCODING)
        y_byte = int(((self._y - MIN_Y) / (MAX_Y - MIN_Y)) * MAX_ENCODING)
        w_byte = int(((self._w - MIN_W) / (MAX_W - MIN_W)) * MAX_ENCODING)
        assert END_KEY not in bytes([first_byte, x_byte, y_byte, w_byte]), \
            "END_KEY appears in message body!!!"
        single_robot_command = bytes([first_byte, x_byte, y_byte, w_byte])
        # print(RobotCommands.deserialize_command(single_robot_command))
        assert(len(single_robot_command) == SINGLE_ROBOT_COMMAND_LENGTH)
        return single_robot_command

    # for debugging/sanity check
    def deserialize_command(command):
        if len(command) != 4:
            raise ValueError("Commands should be 4 bytes")

        first_byte = command[0]
        x_byte = command[1]
        y_byte = command[2]
        w_byte = command[3]

        robot_id = int(first_byte & 15)
        is_dribbling = first_byte & 1 << 5 != 0
        is_charging = first_byte & 1 << 6 != 0
        is_kicking = first_byte & 1 << 7 != 0

        x = (x_byte * ((MAX_X - MIN_X) / MAX_ENCODING)) + MIN_X
        y = (y_byte * ((MAX_Y - MIN_Y) / MAX_ENCODING)) + MIN_Y
        w = (w_byte * ((MAX_W - MIN_W) / MAX_ENCODING)) + MIN_W

        return {
            'is_dribbling': is_dribbling,
            'is_charging': is_charging,
            'is_kicking': is_kicking,
            'x': x,
            'y': y,
            'w': w,
            'robot_id': robot_id
        }

    # Compile a single serialized command message for all 6 robots
    # (static method) takes a dict of {robot_id: robot_commands}
    def get_serialized_team_command(team_commands):
        team_command_message = b""
        num_robots = len(team_commands)
        assert num_robots <= 6, 'too many robots'
        # pad message so it always contains 6 robots worth of data
        # (this is so firmware can deal with constant message length)
        for i in range(6 - num_robots):
            team_command_message += EMPTY_COMMAND
        for robot_id, commands in team_commands.items():
            command_message = commands.get_serialized_command(robot_id)
            # print(RobotCommands.deserialize_command(command_message))
            team_command_message += command_message
        team_command_message = START_KEY + team_command_message + END_KEY
        assert(len(team_command_message) == TEAM_COMMAND_MESSAGE_LENGTH)
        return team_command_message

    # directly set the robot speed fields (ignoring waypoints)
    def set_speeds(self, x, y, w):
        self._x = x
        self._y = y
        self._w = w

    # use the waypoints to calculate desired speeds from robot perspective
    def derive_speeds(self, current_position):
        og_x, og_y, og_w = current_position
        if self.waypoints:
            # if close enough to first waypoint, delete and move to next one
            while len(self.waypoints) > 1 and \
                  self.close_enough(current_position, self.waypoints[0]):
                self.waypoints.pop(0)
            goal_pos, min_speed, max_speed = self.waypoints[0]
            goal_x, goal_y, goal_w = goal_pos
            if min_speed is None:
                min_speed = self.DEFAULT_MIN_SPEED
            if max_speed is None:
                max_speed = self.DEFAULT_MAX_SPEED
            delta = (goal_x - og_x, goal_y - og_y)
            # normalized offsets from robot's perspective
            norm_x, norm_y = self.normalize(og_w, delta)
            norm_w = self.trim_angle(goal_w - og_w)
            # move with speed proportional to delta
            linear_speed = self.magnitude(delta) * self.SPEED_SCALE
            # only use if pid is crappy
            linear_speed = min_speed + linear_speed
            if linear_speed > max_speed:
                linear_speed = max_speed
            self._x = linear_speed * norm_x
            self._y = linear_speed * norm_y
            self._z = norm_w * self.ROTATION_SPEED_SCALE,

    # used for eliminating intermediate waypoints
    def close_enough(self, current, goal):
        cx, cy, cw = current
        gx, gy, gw = current
        dx, dy, dw = abs(cx - gx), abs(cy - gy), abs(cw - gw)
        # for now ignoring rotation
        DISTANCE_THRESHOLD = 10
        return (dx + dy) ** .5 < DISTANCE_THRESHOLD

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
        """Transforms angle into range -pi to pi, for shortest turning"""
        while angle > 2 * math.pi:
            angle -= 2 * math.pi
        while angle < -1 * math.pi:
            angle += 2 * math.pi
        if angle > math.pi:
            angle -= 2 * math.pi
        if angle < -math.pi:
            angle += 2 * math.pi
        return angle

    def __str__(self):
        return "dribble: {}, charge: {}, kick: {} (x, y, w): ({}, {}, {})".format(
            self.is_dribbling,
            self.is_charging,
            self.is_kicking,
            self._x,
            self._y,
            self._w
        )