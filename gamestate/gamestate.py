import time
import traceback
import threading
import numpy as np
from collections import deque
# import RobotCommands from the comms folder
# (expected to run from root directory, use try/except if run from here)
from comms import RobotCommands

# RAW DATA PROCESSING CONSTANTS
BALL_POS_HISTORY_LENGTH = 100
BALL_LOST_TIME = .1
ROBOT_POS_HISTORY_LENGTH = 20
# time after which robot is considered lost by gamestate
ROBOT_LOST_TIME = .2
# time after which lost robot is deleted from the gamestate
ROBOT_REMOVE_TIME = 5

# FIELD + ROBOT DIMENSIONS (mm)
FIELD_SCALE = 1  # useful if using a miniature field
FIELD_X_LENGTH = 9000 * FIELD_SCALE
FIELD_Y_LENGTH = 6000 * FIELD_SCALE
FIELD_MIN_X = -FIELD_X_LENGTH / 2
FIELD_MAX_X = FIELD_X_LENGTH / 2
FIELD_MIN_Y = -FIELD_Y_LENGTH / 2
FIELD_MAX_Y = FIELD_Y_LENGTH / 2
CENTER_CIRCLE_RADIUS = 495 * FIELD_SCALE
GOAL_WIDTH = 1000 * FIELD_SCALE
DEFENSE_AREA_X_LENGTH = 1000 * FIELD_SCALE
DEFENSE_AREA_Y_LENGTH = 2000 * FIELD_SCALE
BALL_RADIUS = 21 * 1.5
ROBOT_RADIUS = 90 * 1.5  # in most cases model robot as circle
# front of robot is actually flatter - use this for dribbling logic
ROBOT_DRIBBLER_RADIUS = 80
ROBOT_FRONT_ANGLE = np.arccos(ROBOT_DRIBBLER_RADIUS / ROBOT_RADIUS)
# PHYSICS CONSTANTS
# ball constant slowdown due to friction
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
        self._game_loop_sleep = None
        self._last_step_time = None

        # RAW POSITION DATA (updated by vision data or simulator)
        # [most recent data is stored at the front of the queue]
        # queue of (time, pos) where positions are in the form np.array([x, y])
        self._ball_position = deque([], BALL_POS_HISTORY_LENGTH)
        # robot positions are np.array([x, y, w]) where w = rotation
        self._blue_robot_positions = dict()  # Robot ID: queue of (time, pos)
        self._yellow_robot_positions = dict()  # Robot ID: queue of (time, pos)

        # Commands data (desired robot actions)
        self._blue_robot_commands = dict()  # Robot ID: commands object
        self._yellow_robot_commands = dict()  # Robot ID: commands object

        # Game status/events
        self.game_clock = None
        self.is_blue_defense_side_left = True
        # TODO: enum all ref box restart commands

        # UI Inputs - set from visualizer
        self.user_click_position = None
        self.user_drag_vector = None
        self.user_selected_robot = None  # (team, id) of robot
        self.user_selected_ball = False
        self.user_charge_command = False
        self.user_kick_command = False
        self.user_dribble_command = False

    def start_game(self, loop_sleep):
        self._game_loop_sleep = loop_sleep
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
                if delta_time > self._game_loop_sleep * 3:
                    print("Game loop large delay: " + str(delta_time))
            self._last_step_time = time.time()

            self.game_clock += delta_time

            # yield to other threads
            time.sleep(self._game_loop_sleep)

    # GAME STATUS/EVENT FUNCTIONS
    def wait_until_game_begins(self):
        while self.game_clock is None:
            time.sleep(.01)

    # RAW DATA GET/SET FUNCTIONS
    # returns position ball was last seen at, or (0, 0) if unseen
    def get_ball_position(self):
        if len(self._ball_position) == 0:
            # print("getting ball position but ball never seen?!?")
            return np.array([0, 0])
        timestamp, pos = self._ball_position[0]
        return pos

    def clear_ball_position(self):
        self._ball_position = deque([], BALL_POS_HISTORY_LENGTH)

    def update_ball_position(self, pos, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        assert(len(pos) == 2 and type(pos) == np.ndarray)
        pos = pos.copy().astype(float)
        self._ball_position.appendleft((timestamp, pos))

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

    # returns position robot was last seen at
    def get_robot_position(self, team, robot_id):
        robot_positions = self.get_team_positions(team)
        if robot_id not in robot_positions:
            # is_robot_lost should be used to check if robot exists
            # here we return a position to avoid crashing the program
            # print("getting position of robot never seen?!?")
            # print("team: {}, id: {}".format(team, robot_id))
            # traceback.print_stack()
            return np.array([0, 0, 0])
        timestamp, pos = robot_positions[robot_id][0]
        return pos

    def get_robot_direction(self, team, robot_id):
        x, y, w = self.get_robot_position(team, robot_id)
        direction = np.array([np.cos(w), np.sin(w)])
        return direction / np.linalg.norm(direction)

    # returns a list of ((team, robot_id), position) for iteration
    def get_all_robot_positions(self):
        all_robot_positions = []
        for team in ['blue', 'yellow']:
            for robot_id in self.get_robot_ids(team):
                robot_pos = self.get_robot_position(team, robot_id)
                if robot_pos is not None:
                    key = (team, robot_id)
                    all_robot_positions.append((key, robot_pos))
        return all_robot_positions

    def update_robot_position(self, team, robot_id, pos):
        assert(len(pos) == 3 and type(pos) == np.ndarray)
        pos = pos.copy().astype(float)
        robot_positions = self.get_team_positions(team)
        if robot_id not in robot_positions:
            # assert(len(robot_positions) <= 6)
            robot_positions[robot_id] = deque([], ROBOT_POS_HISTORY_LENGTH)
        robot_positions[robot_id].appendleft((time.time(), pos))

    def remove_robot(self, team, robot_id):
        team_positions = self.get_team_positions(team)
        del team_positions[robot_id]
        team_commands = self.get_team_commands(team)
        del team_commands[robot_id]

    def get_robot_last_update_time(self, team, robot_id):
        robot_positions = self.get_team_positions(team)
        if robot_id not in robot_positions:
            # print("getting update time of robot never seen?!?")
            return None
        timestamp, pos = robot_positions[robot_id][0]
        # remove lost robots after a while
        if time.time() - timestamp > ROBOT_REMOVE_TIME:
            self.remove_robot(team, robot_id)
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

    def robot_max_speed(self, team, robot_id):
        # in the future this could vary between teams/robots?
        return RobotCommands.ROBOT_MAX_SPEED

    # returns a list of ((team, robot_id), commands) for iteration
    def get_all_robot_commands(self):
        all_robot_commands = []
        for team in ['blue', 'yellow']:
            for robot_id in self.get_robot_ids(team):
                robot_commands = self.get_robot_commands(team, robot_id)
                key = (team, robot_id)
                all_robot_commands.append((key, robot_commands))
        return all_robot_commands

    # GAME RULES FUNCTIONS
    # TODO write a "is_goalie(self, team, robot_id)" function to determine
    # whether the robot of interest is a goalie.
    def is_goalie(self, team, robot_id):
        return False

    # returns bottom left corner of defense area
    def defense_area_corner(self, team):
        if team == "blue" and self.is_blue_defense_side_left or \
           team == "yellow" and not self.is_blue_defense_side_left:
            min_x = FIELD_MIN_X
        else:
            min_x = FIELD_MAX_X - DEFENSE_AREA_X_LENGTH
        min_y = -DEFENSE_AREA_Y_LENGTH / 2
        return np.array([min_x, min_y])

    def is_in_defense_area(self, pos, team):
        min_x, min_y = self.defense_area_corner(team)
        # defense area is a box centered at y = 0
        return ((min_x <= pos[0] <= min_x + DEFENSE_AREA_X_LENGTH) and
                min_y <= pos[1] <= min_y + DEFENSE_AREA_Y_LENGTH)

    def is_in_play(self, pos):
        return ((FIELD_MIN_X <= pos[0] <= FIELD_MAX_X) and
                (FIELD_MIN_Y <= pos[1] <= FIELD_MAX_Y))

    def is_pos_in_bounds(self, pos, team, robot_id):
        # TODO: during free kicks must be away from opponent area
        # + ALL OTHER RULES
        is_defender_too_close = self.is_in_defense_area(pos, team) and \
                not self.is_goalie(team, robot_id)
        return self.is_in_play(pos) and not is_defender_too_close

    # ANALYSIS FUNCTIONS
    # returns the amount of overlap between circles as (x, y) vector
    def overlap(self, pos1, pos2, radius_sum):
        delta = pos2[:2] - pos1[:2]
        if not delta.any():
            return np.array([radius_sum, 0])
        distance = np.linalg.norm(delta)
        if distance <= radius_sum:
            touching_delta = delta / distance * radius_sum
            return touching_delta - delta
        return np.array([0, 0])

    # overlap between two robots
    def robot_overlap(self, pos1, pos2, buffer_dist=0):
        return self.overlap(pos1, pos2, ROBOT_RADIUS * 2 + buffer_dist)

    # if position is in front face of robot
    def is_robot_front_sector(self, robot_pos, pos):
        dx, dy = pos[:2] - robot_pos[:2]
        angle = np.arctan2(dy, dx)
        dw = angle - robot_pos[2]
        return np.cos(dw) * ROBOT_RADIUS > ROBOT_DRIBBLER_RADIUS

    # overlap between robot and ball
    def robot_ball_overlap(self, robot_pos, ball_pos=None):
        if ball_pos is None:
            ball_pos = self.get_ball_position()
        # account for flat front of robot in this case
        delta = ball_pos - robot_pos[:2]
        dx, dy = delta
        dw = np.arctan2(dy, dx) - robot_pos[2]
        if self.is_robot_front_sector(robot_pos, ball_pos):
            # we are in the front sector, so use linear displacement
            robot_dx = np.linalg.norm(delta) * np.cos(dw)
            overlap = ROBOT_DRIBBLER_RADIUS + BALL_RADIUS - robot_dx
            overlap = max(0, overlap)
            w = robot_pos[2]
            return np.array([overlap * np.cos(w), overlap * np.sin(w)])
        return self.overlap(robot_pos, ball_pos, ROBOT_RADIUS + BALL_RADIUS)

    # overlap of position and ball
    def ball_overlap(self, pos):
        ball_pos = self.get_ball_position()
        return self.overlap(pos, ball_pos, BALL_RADIUS)

    # returns the x, y position in center of robot's dribbler
    def dribbler_pos(self, team, robot_id):
        x, y, w = self.get_robot_position(team, robot_id)
        direction = np.array([np.cos(w), np.sin(w)])
        relative_pos = direction * (ROBOT_DRIBBLER_RADIUS + BALL_RADIUS)
        return np.array([x, y]) + relative_pos

    def dribbler_to_robot_pos(self, dribbler_pos, robot_w):
        direction = np.array([np.cos(robot_w), np.sin(robot_w)])
        # divide radius by 2 to go a bit closer to the ball to help make contact
        x, y = dribbler_pos - direction * (ROBOT_DRIBBLER_RADIUS + BALL_RADIUS / 2)
        return np.array([x, y, robot_w])

    # if ball is in position to be dribbled
    def ball_in_dribbler_single_frame(self, team, robot_id, ball_pos=None):
        if ball_pos is None:
            ball_pos = self.get_ball_position()
        robot_pos = self.get_robot_position(team, robot_id)
        ideal_pos = self.dribbler_pos(team, robot_id)
        # print("id {}, ball {} want {}".format(robot_id, ball_pos, ideal_pos))
        # TODO: kicking version of this function incorporates breakbeam sensor?
        MAX_DIST = ROBOT_RADIUS + 32  # fairly lenient constants,
        DRIBBLE_ZONE_RADIUS = 60
        in_zone = np.linalg.norm(ball_pos - ideal_pos) < DRIBBLE_ZONE_RADIUS
        close_enough = np.linalg.norm(ball_pos - robot_pos[:2]) < MAX_DIST
        #print(close_enough)
        return in_zone and close_enough

    def ball_in_dribbler(self, team, robot_id):
        positions = self._ball_position
        MIN_TIME_INTERVAL = 1
        i = 0
        if len(positions) <= 1:
            return False
        if not self.ball_in_dribbler_single_frame(team, robot_id, positions[0][1]):
            return False
        # look back from 0 (most recent) until big enough interval
        while i < len(positions) - 1 and \
              positions[0][0] - positions[i][0] < MIN_TIME_INTERVAL:
            ball_pos = positions[i][1]
            i += 1
            if not self.ball_in_dribbler_single_frame(team, robot_id, ball_pos):
                return False
        return True

    # return whether robot can be in a location without colliding another robot
    def is_position_open(self, pos, team, robot_id, buffer_dist=0):
        for key, robot_pos in self.get_all_robot_positions():
            if key == (team, robot_id):
                continue
            if self.robot_overlap(pos, robot_pos, buffer_dist).any():
                return False
        return True

    # return robot team and id occupying a current position, if any
    def robot_at_position(self, pos):
        for (team, robot_id), robot_pos in self.get_all_robot_positions():
            if self.overlap(pos, robot_pos, ROBOT_RADIUS).any():
                return (team, robot_id)
        return None

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
        # print(f"{velocity_initial}")
        if not velocity_initial.any():
            return (self.get_ball_position())
        accel_direction = -velocity_initial / np.linalg.norm(velocity_initial)
        accel = accel_direction * BALL_DECCELERATION
        # truncate if we're going past the time where the ball would stop
        velocity_final = accel * delta_time + velocity_initial
        if ((velocity_initial * velocity_final) < 0).any():
            assert(((velocity_initial * velocity_final) <= 0).all())
# We need to use two cases here because one coordinate of initial velocity can be zero which
# would cause us to divide by zero if we use that axis.
            if not accel[0] == 0:
                time_to_stop = -1 * velocity_initial[0] / accel[0]
            else:
                time_to_stop = -1 * velocity_initial[1] / accel[1]
            # print("dt: {} TTS: {}".format(delta_time, time_to_stop))
            delta_time = time_to_stop
        predicted_pos_change = \
            0.5 * accel * delta_time ** 2 + velocity_initial * delta_time
        # print("dt: {} PPC: {}".format(delta_time, predicted_pos_change))
        predicted_pos = predicted_pos_change + self.get_ball_position()
        return predicted_pos

    # return a random position inside the field
    def random_position(self):
        return (np.random.randint(0, FIELD_X_LENGTH),
                np.random.randint(0, FIELD_Y_LENGTH))

    def is_pos_valid(self, pos, team, robot_id):
        return self.is_position_open(pos, team, robot_id) and \
            self.is_pos_in_bounds(pos, team, robot_id)

    # returns the top and bottom goalposts for a team
    def get_defense_goal(self, team):
        if (self.is_blue_defense_side_left and team == 'blue') or \
           (not self.is_blue_defense_side_left and team == 'yellow'):
            return (np.array([FIELD_MIN_X, GOAL_WIDTH/2]),
                    np.array([FIELD_MIN_X, -GOAL_WIDTH/2]))
        else:
            return (np.array([FIELD_MAX_X, GOAL_WIDTH/2]),
                    np.array([FIELD_MAX_X, -GOAL_WIDTH/2]))

    def get_attack_goal(self, team):
        if team == 'yellow':
            return self.get_defense_goal('blue')
        else:
            assert(team == 'blue')
            return self.get_defense_goal('yellow')

    # return where in goal ball is going to if it is going in
    def is_shot_coming(self, team):
        start_ball_pos = self.get_ball_position()
        start_x = start_ball_pos[0]
        start_y = start_ball_pos[1]
        final_ball_pos = self.predict_ball_pos(2)
        final_x = final_ball_pos[0]
        final_y = final_ball_pos[1]
        defense_goal = self.get_defense_goal(team)
        x_pos_of_goal = defense_goal[0][0]
        if min(final_x, start_x) <= x_pos_of_goal <= max(final_x, start_x):
            slope = (start_y - final_y)/(start_x - final_x)
            y_intercept = slope * (x_pos_of_goal - start_x) + start_y
            if -GOAL_WIDTH/2 <= y_intercept <= GOAL_WIDTH/2:
                return np.array([x_pos_of_goal, y_intercept])
        return None
