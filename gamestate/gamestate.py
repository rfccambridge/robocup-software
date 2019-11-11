import time
import threading
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
ROBOT_DIAMETER = 180


class GameState(object):
    """Game state contains all raw game information in one place.
       Functions involving physics and game rules go in gamestate.
       Many threads can edit and use the game state at once, cuz Python GIL
       Since using python, data types are specified in the comments below.
    """
    def __init__(self):
        # NOTE: Fields starting with _underscore are "private" so
        # should be accessed through getter and setter methods

        # Thread keeps track of game status/events
        self._is_playing = False
        self._game_thread = None
        self._last_step_time = None

        # RAW POSITION DATA (updated by vision data or simulator)
        # [most recent data is stored at the front of the queue]
        # queue of (time, pos), where positions are in the form np.array([x, y])
        self._ball_position = deque([], BALL_POS_HISTORY_LENGTH)
        # robot positions are np.array([x, y, w]) where w = rotation
        self._blue_robot_positions = dict()  # Robot ID: queue of (time, pos)
        self._yellow_robot_positions = dict()  # Robot ID: queue of (time, pos)

        # Commands data (desired robot actions)
        self._blue_robot_commands = dict()  # Robot ID: commands object
        self._yellow_robot_commands = dict()  # Robot ID: commands object

        # Game status/events
        self.game_clock = None
        # TODO: enum all ref box restart commands
        self.user_click_field = None

    def start_game(self):
        self._is_playing = True
        self._game_thread = threading.Thread(target=self.game_loop)
        # set to daemon mode so it will be easily killed
        self._game_thread.daemon = True
        self._game_thread.start()

    def end_game(self):
        if self._is_playing:
            self._is_playing = False
            self._game_thread.join()
            self._game_thread = None

    def game_loop(self):
        # set up game status
        self.game_clock = 0
        while self._is_playing:
            delta_time = 0
            if self._last_step_time is not None:
                delta_time = time.time() - self._last_step_time
                if delta_time > .3:
                    print("Game loop large delay: " + str(delta_time))
            self._last_step_time = time.time()

            self.game_clock += delta_time
            # yield to other threads - loop at most 10 times per second
            time.sleep(.1)

    # GAME STATUS/EVENT FUNCTIONS
    def wait_until_game_begins(self):
        while self.game_clock is None:
            time.sleep(.01)

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
    # TODO write a "is_goalie(self, team, robot_id)" function to determine
    # whether the robot of interest is a goalie.
    def is_goalie(self, team, robot_id):
        return False

    def is_pos_in_bounds(self, pos, team, robot_id):
        in_play = (-FIELD_W / 2 <= pos[0] <= FIELD_W / 2) and \
            (-FIELD_H / 2 <= pos[1] <= FIELD_H / 2)
        in_goalie_area = False
        if (-4500 <= pos[0] <= -3500) or (3500 <= pos[0] <= 4500):
            if -1000 <= pos[1] <= 1000:
                in_goalie_area = True
        if not in_play:
            return False
        return self.is_goalie(self, team, robot_id) or (not in_goalie_area)

    # ANALYSIS FUNCTIONS
    # return whether robot can be in a location without colliding another robot
    def is_position_open(self, pos):
        all_robot_positions = []
        for team in ['blue', 'yellow']:
            for robot_id in self.get_robot_ids(team):
                # get just the x, y for this robot
                pos = self.get_robot_position(team, robot_id)[:1]
                all_robot_positions.append(pos)
        for robot_pos in all_robot_positions:
            if np.linalg.norm(pos - robot_pos) <= ROBOT_DIAMETER:
                return False
        return True

    # Here we find ball velocities from ball position data
    def get_ball_velocity(self):
        # TOOD: smooth out this value by averaging?
        # prev_velocity = self.ball_velocity
        positions = self._ball_position
        MIN_TIME_INTERVAL = .05
        i = 0
        if len(positions) <= 1:
            return np.array([0, 0])

        # look back from 0 (most recent) until big enough interval
        while i < len(positions) - 1 and \
              positions[0][0] - positions[i][0] < MIN_TIME_INTERVAL:
            i += 1
        delta_pos = positions[0][1] - positions[i][1]
        delta_time = positions[0][0] - positions[i][0]

        return delta_pos / delta_time

    def predict_ball_pos(self, delta_time):
        # estimate for acceleration due to friction as the ball rolls
        accel_magnitude = -1000  # -500 seems more accurate
        velocity_initial = self.get_ball_velocity()
        if not velocity_initial.any():
            return (self.get_ball_position())
        accel_direction = velocity_initial / np.linalg.norm(velocity_initial)
        accel = accel_direction * accel_magnitude
        # truncate if we're going past the time where the ball would stop
        if accel[0] * delta_time + velocity_initial[0] < 0:
            time_to_stop = -1 * velocity_initial[0] / accel[0]
            # print("dt: {} TTS: {}".format(delta_time, time_to_stop))
            delta_time = time_to_stop
        # TODO WACK: for small dt i.e. simulation steps, acceleration must
        # be doubled to account for lag in velocity calculation
        if delta_time < .1:
            accel *= 2
        predicted_pos_change = \
            0.5 * accel * delta_time ** 2 + velocity_initial * delta_time
        # print("dt: {} PPC: {}".format(delta_time, predicted_pos_change))
        predicted_pos = predicted_pos_change + self.get_ball_position()
        return predicted_pos

    def get_ball_interception_point(self, team, robot_id):
        robot_pos = self.get_robot_position(team, robot_id)
        delta_t = .05
        robot_max_speed = 500
        time = 0
        while(True):
            interception_pos = self.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos - interception_pos)
            if separation_distance <= time * robot_max_speed:
                return interception_pos
            else:
                time += delta_t

    def is_pos_valid(self, pos, team, robot_id):
        if self.is_position_open(pos) and self.is_pos_in_bounds(pos, team, robot_id):
            return True
        return False
