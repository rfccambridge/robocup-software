import time
import numpy as np
from collections import deque
# import RobotCommands from the comms folder
# (expected to run from root directory, use try/except if run from here)
from comms import RobotCommands

BALL_POS_HISTORY_LENGTH = 20
BALL_LOST_TIME = .1
ROBOT_POS_HISTORY_LENGTH = 20
ROBOT_LOST_TIME = .2

FIELD_W = 9000
FIELD_H = 6000


class GameState(object):
    """Game state contains all raw game information in one place. Also, all
       functions involving physics and game rules go in gamestate.
       Many threads can edit and use the game state at once, cuz Python GIL
       Since using python, data types are specified in the comments below.
    """
    def __init__(self):
        # NOTE: Fields starting with _underscore are "private" so
        # should be accessed through getter and setter methods

        # RAW POSITION DATA (updated by vision data or simulator)
        # [most recent data is stored at the front of the queue]
        # queue of (time, pos), where positions are in the form np.array([x, y])
        self._ball_position = deque([], BALL_POS_HISTORY_LENGTH)
        # robot positions are np.array([x, y, w]) where w = rotation
        self._blue_robot_positions = dict()  # Robot ID: queue of (time, pos)
        self._yellow_robot_positions = dict()  # Robot ID: queue of (time, pos)
        # TODO: store both teams robots
        # TODO: include game states/events, i.e. time, score and referee

        # Commands data (desired robot actions)
        self._blue_robot_commands = dict()  # Robot ID: commands object
        self._yellow_robot_commands = dict()  # Robot ID: commands object

        # TODO: cached analysis data (i.e. ball trajectory)
        # this can be later, for now just build the functions
        self.ball_velocity = np.array([0, 0])

        # User input
        self.user_click_field = None

    # RAW DATA GET/SET FUNCTIONS
    # returns position ball was last seen at
    def get_ball_position(self):
        if len(self._ball_position) == 0:
            # print("getting ball position but ball never seen?!?")
            return None
        timestamp, pos = self._ball_position[0]
        return pos

    def update_ball_position(self, pos):
        assert(len(pos) == 2 and type(pos) == np.ndarray)
        self._ball_position.appendleft((time.time(), pos))

    def get_ball_last_update_time(self):
        if len(self._ball_position) == 0:
            # print("getting ball update time but ball never seen?!?")
            return None
        timestamp, pos = self._ball_position[0]
        return timestamp

    def is_ball_lost(self):
        last_update_time = self.get_ball_last_update_time()
        if last_update_time is None:
            return True
        return time.time() - last_update_time > BALL_LOST_TIME

    def get_robot_positions(self, team):
        if team == 'blue':
            return self._blue_robot_positions
        else:
            assert(team == 'yellow')
            return self._yellow_robot_positions

    def get_robot_ids(self, team):
        robot_positions = self.get_robot_positions(team)
        return tuple(robot_positions.keys())

    # returns position robot was last seen at
    def get_robot_position(self, team, robot_id):
        robot_positions = self.get_robot_positions(team)
        if robot_id not in robot_positions:
            # print("getting position of robot never seen?!?")
            return None
        timestamp, pos = robot_positions[robot_id][0]
        return pos

    def update_robot_position(self, team, robot_id, pos):
        assert(len(pos) == 3 and type(pos) == np.ndarray)
        robot_positions = self.get_robot_positions(team)
        if robot_id not in robot_positions:
            robot_positions[robot_id] = deque([], ROBOT_POS_HISTORY_LENGTH)
        robot_positions[robot_id].appendleft((time.time(), pos))

    def get_robot_last_update_time(self, team, robot_id):
        robot_positions = self.get_robot_positions(team)
        if robot_id not in robot_positions:
            # print("getting update time of robot never seen?!?")
            return None
        timestamp, pos = robot_positions[robot_id][0]
        return timestamp

    # check if robot hasn't been seen by cameras in a while
    def is_robot_lost(self, team, robot_id):
        last_update_time = self.get_robot_last_update_time(team, robot_id)
        if last_update_time is None:
            return True
        return time.time() - last_update_time > ROBOT_LOST_TIME

    def get_team_commands(self, team):
        if team == 'blue':
            return self._blue_robot_commands
        else:
            assert(team == 'yellow')
            return self._yellow_robot_commands

    def get_robot_commands(self, team, robot_id):
        team_commands = self.get_team_commands(team)
        if robot_id not in team_commands:
            team_commands[robot_id] = RobotCommands()
        return team_commands[robot_id]

    # GAME RULES FUNCTIONS
    #TODO write a "is_goalie(self, team, robot_id)" function to determine whether the robot of interest is a goalie.
    def is_goalie(self, team, robot_id):
        return False

    def is_pos_in_bounds(self, pos, team, robot_id):
        in_play = False
        in_goalie_area = False
        if (-4500 <= pos[0] <= 4500) and (-3000 <= pos[1] <= 3000):
            in_play = True
        if (-4500 <= pos[0] <= -3500) or (3500 <= pos[0] <= 4500):
            if -1000 <= pos[1] <= 1000:
                in_goalie_area = True
        if in_play == False:
            return False
        elif self.is_goalie(self, team, robot_id) == False and in_goalie_area == True:
            return False
        else:
            return True

    # ANALYSIS FUNCTIONS
    # return whether robot can be in a location
    def is_position_open(self, pos):
        robot_diameter = 180
        for id in self.get_robot_ids(yellow):
            obstacle_pos = self._yellow_robot_positions[id][0][1][:1]
# obstacle_pos is a tuple (x, y). We are taking the first element of the queue (ie most recent entry), then
# the second entry in the tuple (ie the pos), and then the first 2 entries of pos (ie (x, y))
            if np.linalg.norm(pos - obstacle_pos) <= robot_diameter:
                return False
        for id in self.get_robot_ids(blue):
            obstacle_pos = self._blue_robot_positions[id][0][1][:2]
            if self.magnitude(pos - obstacle_pos) <= robot_diameter:
                return False
        return True

    # Here we find ball velocities from ball position data
    def get_ball_velocity(self):
        prev_velocity = self.ball_velocity

        positions = self._ball_position
        MIN_TIME_INTERVAL = .05
        i = 0
        if len(positions) <= 1:
            return np.array([0, 0])
        # 0 is most recent!!!
        while i < len(positions) - 1 and  positions[0][0] - positions[i][0] < MIN_TIME_INTERVAL:
            i += 1
        delta_pos = positions[0][1] - positions[i][1]
        delta_time = (positions[0][0] - positions[i][0])

        self.ball_velocity = delta_pos / delta_time

        return self.ball_velocity

    def get_ball_pos_future(self, seconds):
        # -500 seems more accurate
        accel_magnitude = -1000
        #This is just a guess at the acceleration due to friction as the ball rolls. This number should be tuned empitically.
        velocity_initial = self.get_ball_velocity()
        # dumb check to prevent erroring out, think of something nicer
        if not velocity_initial.any():
            return (self.get_ball_position())
        accel_direction = velocity_initial / np.linalg.norm(velocity_initial)
        accel = accel_direction * accel_magnitude
# we need to check if our acceleration would make the ball turn around. If this happens we will need to truncate
# the time at the point where velocoty is zero.
        if accel[0] * seconds + velocity_initial[0] < 0:
            time_to_stop = -1 * velocity_initial[0] / accel[0]
            predicted_pos_change = accel * time_to_stop ** 2 + \
                                            velocity_initial *time_to_stop
            predicted_pos = predicted_pos_change + self.get_ball_position()
            return predicted_pos
            # TOOD: infinite recursion right now
            # return self.get_ball_pos_future(time_to_stop)
        else:
            predicted_pos_change = accel *seconds ** 2 + \
                                            velocity_initial * seconds
            predicted_pos = predicted_pos_change + self.get_ball_position()
            return predicted_pos

    def get_ball_interception_point(self, team, robot_id):
        robot_pos = self.get_robot_position(team, robot_id)
        delta_t = .05
        robot_max_speed = 500
        time = 0
        while(True):
            interception_pos = self.get_ball_pos_future(time)
            separation_distance = np.linalg.norm(robot_pos - interception_pos)
            if separation_distance <= time * robot_max_speed:
                return interception_pos
            else:
                time += delta_t

    def is_pos_valid(self, pos, team, robot_id):
        if self.is_position_open(pos) and self.is_pos_in_bounds(pos, team, robot_id):
            return True
        return False
