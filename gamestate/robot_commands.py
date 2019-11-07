import math
import numpy as np

# default proportional scaling constant for distance differences
SPEED_SCALE = .8
# Max speed from max power to motors => [free-spinning] 1090 mm/s (see firmware)
# Reduce that by multiplying by min(sin(theta), cos(theta)) of wheels
# Goal is to get upper bound on we can send and expect firmware to obey accurately
DEFAULT_MAX_SPEED = 650 # pretty conservative, maybe we can be more aggressive?
DEFAULT_MIN_SPEED = 50
# TODO: make rotation actually work
ROTATION_SPEED_SCALE = 0

# Serialization constants
MIN_X = -1000
MAX_X = 1000
MIN_Y = -1000
MAX_Y = 1000
MIN_W = -2 * math.pi
MAX_W = 2 * math.pi
MAX_ENCODING = 256

class RobotCommands:
    # for padding multi-robot commands - 15 should be higher than any valid robot_id
    EMPTY_COMMAND = bytearray([15, 0, 0, 0])
    
    def __init__(self):
        # each waypoint is (pos, speed)?
        self.waypoints = []
        # (private) actual speed values from robot's perspective, derived from waypoints
        self._x = 0 # speed x mm/s
        self._y = 0 # speed y mm/s
        self._w = 0 # speed robot radians/s
        # other commands
        self.is_dribbling = False
        self.is_charging = False
        self.is_kicking = False    

    def get_serialized_command(self, robot_id):
        if not MIN_X < self._x < MAX_X:
            raise ValueError("x={} is too big to be serialized".format(self._x))
        if not MIN_Y < self._y < MAX_Y:
            raise ValueError("y={} is too big to be serialized".format(self._y))
        if not MIN_W < self._w < MAX_W:
            raise ValueError("w={} is too big to be serialized".format(self._w))
        if robot_id < 0 or robot_id > 14:
            raise ValueError("robot_id={} is too large to serialize".format(robot_id))
 
        first_byte = 0
        first_byte = first_byte | (15 & robot_id) # The 4 least significant bits
        first_byte = first_byte | int(self.is_dribbling) << 5 # Bit 5
        first_byte = first_byte | int(self.is_charging) << 6 # Bit 6
        first_byte = first_byte | int(self.is_kicking) << 7 # Bit 7
        
        x_byte = int(((self._x - MIN_X) / (MAX_X - MIN_X)) * MAX_ENCODING)
        y_byte = int(((self._y - MIN_Y) / (MAX_Y - MIN_Y)) * MAX_ENCODING)
        w_byte = int(((self._w - MIN_W) / (MAX_W - MIN_W)) * MAX_ENCODING)
        return bytes([first_byte, x_byte, y_byte, w_byte])

    # for debugging/sanity check
    def deserialize_command(self, command):
        if len(command) != 4:
            raise ValueError("Commands should be 4 bytes")
       
        first_byte = command[0]
        x_byte = command[1]
        y_byte = command[2]
        w_byte = command[3]
 
        robot_id = int(first_byte & 15)
        is_dribbling = first_byte & 1 << 5 !=0
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
        
    # set the robot to stop
    def set_zero_speeds(self):
        self._x = 0
        self._y = 0
        self._z = 0
        
    # use the waypoints to calculate desired speeds from robot perspective
    def derive_speeds(self, current_position):
        og_x, og_y, og_w = current_position
        if self.waypoints:
            # if close enough to first waypoint, delete and move to next one
            while len(self.waypoints) > 1 and \
                  self.close_enough(current_position, self.waypoints[0]):
                waypoints.pop(0)
            goal_pos, min_speed, max_speed = self.waypoints[0]
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
            self._x = linear_speed * norm_x
            self._y = linear_speed * norm_y
            self._z = norm_w * ROTATION_SPEED_SCALE,
        
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
        
