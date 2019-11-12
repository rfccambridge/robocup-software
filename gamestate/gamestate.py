import time
import threading
import numpy as np
from collections import deque
# import RobotCommands from the comms folder
# (expected to run from root directory, use try/except if run from here)
from comms import RobotCommands

# RAW DATA PROCESSING CONSTANTS
BALL_POS_HISTORY_LENGTH = 20
BALL_LOST_TIME = .1
ROBOT_POS_HISTORY_LENGTH = 20
ROBOT_LOST_TIME = .2

# FIELD + ROBOT DIMENSIONS
FIELD_W = 9000
FIELD_H = 6000
ROBOT_DIAMETER = 180

# PHYSICS CONSTANTS
# models constant slowdown due to friction
BALL_DECCELERATION = 350  # mm/s^2


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
        pos = pos.copy().astype(float)
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

    def get_team_positions(self, team):
        if team == 'blue':
            return self._blue_robot_positions
        else:
            assert(team == 'yellow')
            return self._yellow_robot_positions

    def get_robot_ids(self, team):
        robot_positions = self.get_team_positions(team)
        return tuple(robot_positions.keys())

    # returns a list of all robot positions
    def get_all_robot_positions(self):
        all_robot_positions = []
        for team in ['blue', 'yellow']:
            for robot_id in self.get_robot_ids(team):
                # get just the x, y for this robot
                robot_pos = self.get_robot_position(team, robot_id)
                all_robot_positions.append(robot_pos)
        return all_robot_positions

    # returns position robot was last seen at
    def get_robot_position(self, team, robot_id):
        robot_positions = self.get_team_positions(team)
        if robot_id not in robot_positions:
            # print("getting position of robot never seen?!?")
            return None
        timestamp, pos = robot_positions[robot_id][0]
        return pos

    def update_robot_position(self, team, robot_id, pos):
        assert(len(pos) == 3 and type(pos) == np.ndarray)
        pos = pos.copy().astype(float)
        robot_positions = self.get_team_positions(team)
        if robot_id not in robot_positions:
            robot_positions[robot_id] = deque([], ROBOT_POS_HISTORY_LENGTH)
        robot_positions[robot_id].appendleft((time.time(), pos))

    def get_robot_last_update_time(self, team, robot_id):
        robot_positions = self.get_team_positions(team)
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
        if (-FIELD_W / 2 <= pos[0] <= -FIELD_W / 2 + 1000) or \
           (FIELD_W / 2 - 1000 <= pos[0] <= FIELD_W / 2):
            if -1000 <= pos[1] <= 1000:
                in_goalie_area = True
        # TODO: distingush own vs opponnet goalie area
        # TODO: during free kicks must be away from opponent area
        # + ALL OTHER RULES
        if not in_play:
            return False
        return self.is_goalie(team, robot_id) or (not in_goalie_area)

    # ANALYSIS FUNCTIONS
    # returns the amount of overlap between robots as (x, y) vector
    def robot_collision(self, pos1, pos2):
        delta = pos2[:2] - pos1[:2]
        if not delta.any():
            return np.array([ROBOT_DIAMETER, 0])
        distance = np.linalg.norm(delta)
        if distance <= ROBOT_DIAMETER:
            touching_delta = delta / distance * ROBOT_DIAMETER
            return touching_delta - delta
        return np.array([0, 0])

    # return whether robot can be in a location without colliding another robot
    def is_position_open(self, pos):
        for robot_pos in self.get_all_robot_positions():
            if self.robot_collision(pos, robot_pos).any():
                return False
        return True

    # Here we find ball velocity at most recent timestamp from position data
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
        # use those two points as reference for calculation
        time1, pos1 = positions[i]
        time2, pos2 = positions[0]
        delta_pos = pos2 - pos1
        delta_time = time2 - time1
        if delta_pos[0] > 400:
            for time, pos in self._ball_position:
                print(pos)
            assert(False)
        midpoint_velocity = delta_pos / delta_time
        if not midpoint_velocity.any():
            return np.array([0, 0])
        # print("before adjust: {}".format(midpoint_velocity))

        # adjust ball's deceleration since the midpoint of interval used
        midpoint_time = (time1 + time2) / 2
        time_since_midpoint = time2 - midpoint_time
        accel_direction = -midpoint_velocity / np.linalg.norm(midpoint_velocity)
        accel = accel_direction * BALL_DECCELERATION * time_since_midpoint
        velocity_now = midpoint_velocity + accel
        # truncate if slowdown has caused change directions
        if ((velocity_now * midpoint_velocity) < 0).any():
            assert(((velocity_now * midpoint_velocity) <= 0).all())
            velocity_now = np.array([0, 0])
        # print("after adjust: {}".format(velocity_now))
        return velocity_now

    def predict_ball_pos(self, delta_time):
        velocity_initial = self.get_ball_velocity()
        if not velocity_initial.any():
            return (self.get_ball_position())
        accel_direction = -velocity_initial / np.linalg.norm(velocity_initial)
        accel = accel_direction * BALL_DECCELERATION
        # truncate if we're going past the time where the ball would stop
        velocity_final = accel * delta_time + velocity_initial
        if ((velocity_initial * velocity_final) < 0).any():
            assert(((velocity_initial * velocity_final) <= 0).all())
            time_to_stop = -1 * velocity_initial[0] / accel[0]
            # print("dt: {} TTS: {}".format(delta_time, time_to_stop))
            delta_time = time_to_stop
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
        return self.is_position_open(pos) and \
            self.is_pos_in_bounds(pos, team, robot_id)
