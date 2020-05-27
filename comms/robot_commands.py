import math
import numpy as np

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
    # Robot Capability Constants
    # Max speed from max power to motors => [no-load] 1090 mm/s (see firmware)
    # Reduce that by multiplying by min(sin(theta), cos(theta)) of wheels
    # Goal is to get upper bound on what firmware can obey accurately
    ROBOT_MAX_SPEED = 500
    ROBOT_MAX_W = 6.14

    # constants for deriving speed from waypoints
    # default proportional scaling constant for distance differences
    SPEED_SCALE = .9
    ROTATION_SPEED_SCALE = 3

    def __init__(self):
        # maximum speed at which robot will pursue waypoints
        self._speed_limit = self.ROBOT_MAX_SPEED
        # each waypoint is a position (x, y, w)
        self.waypoints = []
        self._prev_waypoint = None
        # (private) speed values from robot's perspective
        self._x = 0  # speed x mm/s
        self._y = 0  # speed y mm/s
        self._w = 0  # speed robot radians/s
        # other commands
        self.is_dribbling = False
        self.is_charging = False
        self.is_kicking = False

    # function for limiting robot speeds in the case of ref commands
    def set_speed_limit(self, speed=None):
        if speed is None:
            speed = self.ROBOT_MAX_SPEED
        self._speed_limit = speed

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
    def deserialize_command(self, command):
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
    def get_serialized_team_command(self, team_commands):
        team_command_message = b""
        num_robots = len(team_commands)
        if len(team_commands) > 6:
            # TODO: handle better?
            print('too many robot ids seen, not sending any commands?')
            num_robots = 0
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

    def clear_waypoints(self):
        self.waypoints = []

    # hacky way to make robot not slow down toward a destination:
    # (append 2 waypoints in the same direction)
    # DEPENDS ON SLOWDOWN LOGIC IN DERIVE_SPEEDS FUNCTION
    def append_urgent_destination(self, pos, current_position):
        direction = pos[:2] - current_position[:2]
        if not direction.any():
            return
        epsilon = 1
        waypoint = pos[:2] - (direction / np.linalg.norm(direction)) * epsilon
        waypoint = np.array([waypoint[0], waypoint[1], pos[2]])
        self.append_waypoint(waypoint, current_position)
        self.append_waypoint(pos, current_position)

    def append_waypoint(self, waypoint, current_position):
        """ 
        Add a new waypoint to the end of the robot waypoint list.
        If w is None, then use some convenient angle.
        """
        if self.waypoints:
            initial_pos = self.waypoints[-1]
        else:
            initial_pos = current_position
        # do not append redundant waypoints
        if (waypoint[:2] == initial_pos[:2]).all() and \
           (waypoint[2] == initial_pos[2] or waypoint[2] is None):
            return
        # print(f"{initial_pos}, {waypoint}")

        x, y, w = waypoint
        if w is None:
            dx, dy = waypoint[:2] - initial_pos[:2]
            linear_distance = np.linalg.norm(np.array([dx, dy]))
            DISTANCE_THRESHOLD = 1000
            # default to face waypoint for longer distances
            if linear_distance > DISTANCE_THRESHOLD:
                dw = np.arctan2(dy, dx) - initial_pos[2]
                w = initial_pos[2] + self.trim_angle_90(dw)
            else:
                w = current_position[2]
        self.waypoints.append(np.array([x, y, w]))

    def set_waypoints(self, waypoints, current_position, is_urgent=False):
        self.clear_waypoints()
        for i, waypoint in enumerate(waypoints):
            if i == (len(waypoints) - 1) and is_urgent:
                self.append_urgent_destination(waypoint, current_position)
            else:
                self.append_waypoint(waypoint, current_position)

    # directly set the robot speed
    def set_speeds(self, x, y, w):
        self._x = x
        self._y = y
        self._w = w

    # predict where the robot will be if it follows the current command
    # command is in robot's perspective
    def predict_pos(self, current_position, delta_time):
        assert(len(current_position) == 3 and type(current_position) == np.ndarray)
        self.derive_speeds(current_position)
        x, y, w = current_position
        robot_x, robot_y = self.field_to_robot_perspective(w, np.array([x, y]))
        robot_x = robot_x + delta_time * self._x
        robot_y = robot_y + delta_time * self._y
        new_w = (w + delta_time * self._w) % (np.pi * 2)
        # transform the x and y back to field perspective
        new_x, new_y = self.robot_to_field_perspective(
            w, np.array([robot_x, robot_y])
        )
        return np.array([new_x, new_y, new_w])

    # use the waypoints to calculate desired speeds from robot perspective
    def derive_speeds(self, current_position):
        if not self.waypoints:
            #self.set_speeds(0, 0, 0)
            return
        og_x, og_y, og_w = current_position
        if self._prev_waypoint is None:
            self._prev_waypoint = current_position
        # if close enough to first waypoint, delete and move to next one
        while len(self.waypoints) > 1 and \
                self.close_enough(current_position, self.waypoints[0]):
            self._prev_waypoint = self.waypoints.pop(0)
        goal_pos = self.waypoints[0]
        goal_x, goal_y, goal_w = goal_pos
        delta = (goal_pos - current_position)[:2]
        # normalized offsets from robot's perspective
        robot_vector = self.field_to_robot_perspective(og_w, delta)
        norm_x, norm_y = self.normalize(robot_vector)
        norm_w = self.trim_angle(goal_w - og_w)
        # move with speed proportional to delta
        linear_speed = self.magnitude(delta) * self.SPEED_SCALE
        # slow down less for intermediate waypoints based on angle
        # (always slows down fully for the final waypoint)
        min_waypoint_speed = 0
        if len(self.waypoints) > 1:
            next_delta = (self.waypoints[1] - goal_pos)[:2]
            if next_delta.any():
                m1 = np.linalg.norm(delta)
                m2 = np.linalg.norm(next_delta)
                # get angle between vectors (arccos -> 0 to pi)
                inner_formula = np.dot(delta, next_delta)/(m1*m2)
                if inner_formula > 1:
                    # catch rounding errors
                    assert(inner_formula - 1 < .001)
                    inner_formula = 1
                trimmed_angle = np.arccos(inner_formula)
                if not (0 <= trimmed_angle <= np.pi):
                    # not sure why this was ever triggering?
                    self.logger.debug("how is trimmed angle:" + str(trimmed_angle))
                    trimmed_angle = max(trimmed_angle, 0)
                    trimmed_angle = min(trimmed_angle, np.pi)
                trimmed_angle = min(trimmed_angle, np.pi / 2)
                # slow down depending on the sharpness of the turn
                # (to a floor for >90 degree turns, keep speed if straight)
                MIN_SLOWDOWN = .15  # (proportion of max speed)
                slowdown_factor = 1 - trimmed_angle / (np.pi / 2)
                slowdown_factor = max(slowdown_factor, MIN_SLOWDOWN)
                assert(slowdown_factor <= 1)
                min_waypoint_speed = self._speed_limit * slowdown_factor
        linear_speed = linear_speed + min_waypoint_speed
        linear_speed = min(linear_speed, self._speed_limit)
        self._x = linear_speed * norm_x
        # print("x: {}, goal_x: {}, vx: {}".format(og_x, goal_x, self._x))
        self._y = linear_speed * norm_y
        self._w = norm_w * self.ROTATION_SPEED_SCALE
        self._w = min(self._w, self.ROBOT_MAX_W)
        self._w = max(self._w, -self.ROBOT_MAX_W)
        # print("w: {}, goal_w: {}, d_w: {}, self_w: {}".format(og_w, goal_w, norm_w, self._w))

    # used for eliminating intermediate waypoints
    def close_enough(self, current, goal):
        # distance condition helpful for simulator b.c. won't overrun waypoint
        DISTANCE_THRESHOLD = 50
        delta = goal - current
        # for now ignoring rotation
        linear_distance = np.linalg.norm(delta[:2])
        is_close = linear_distance < DISTANCE_THRESHOLD
        # is_past will probably be the main one used in real life:
        # move to next waypoint if we've gone past this one
        is_past = False
        if self._prev_waypoint is not None:
            delta_from_prev = current - self._prev_waypoint
            distance_from_prev = np.linalg.norm(delta_from_prev[:2])
            waypoint_delta = goal - self._prev_waypoint
            waypoint_distance = np.linalg.norm(waypoint_delta[:2])
            is_past = distance_from_prev > waypoint_distance
        return is_close or is_past

    # HELPER FUNCTIONS
    # Transforms field dx, dy into a vector in the robot's perspective
    def field_to_robot_perspective(self, w_robot, vector):
        assert(len(vector) == 2 and type(vector) == np.ndarray)
        if not vector.any():
            return vector
        x, y = vector
        w_rot = w_robot - np.arctan2(y, x)
        magnitude = self.magnitude(vector)
        return np.array([np.sin(w_rot) * magnitude, np.cos(w_rot) * magnitude])

    # Transforms robot perspective dx, dy vector into field vector
    def robot_to_field_perspective(self, w_robot, vector):
        assert(len(vector) == 2 and type(vector) == np.ndarray)
        if not vector.any():
            return vector
        x, y = vector
        w_rot = w_robot - np.arctan2(x, y)
        magnitude = self.magnitude(vector)
        return np.array([np.cos(w_rot) * magnitude, np.sin(w_rot) * magnitude])

    def normalize(self, vector):
        assert(len(vector) == 2)
        if not vector.any():
            return vector
        return vector / np.linalg.norm(vector)

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

    def trim_angle_90(self, angle):
        """Transforms angle into range -pi/2 to pi/2, for shortest turning
           Treats 180 degrees reflection as equivalent.
           So resulting angle is facing same or direct opposite of original.
        """
        angle = self.trim_angle(angle)
        if angle > math.pi / 2:
            angle -= math.pi
        if angle < -math.pi / 2:
            angle += math.pi
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
