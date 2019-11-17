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
# time after which robot is considered lost by gamestate
ROBOT_LOST_TIME = .2
# time after which lost robot is deleted from the gamestate
ROBOT_REMOVE_TIME = 5

# FIELD + ROBOT DIMENSIONS (mm)
FIELD_X_LENGTH = 9000
FIELD_Y_LENGTH = 6000
CENTER_CIRCLE_RADIUS = 495
GOAL_WIDTH = 1000
DEFENSE_AREA_X_LENGTH = 1000
DEFENSE_AREA_Y_LENGTH = 2000
BALL_RADIUS = 21
ROBOT_RADIUS = 90

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
        self.is_blue_defense_side_left = True
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

    # returns position robot was last seen at
    def get_robot_position(self, team, robot_id):
        robot_positions = self.get_team_positions(team)
        if robot_id not in robot_positions:
            # print("getting position of robot never seen?!?")
            return None
        timestamp, pos = robot_positions[robot_id][0]
        return pos

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
            assert(len(robot_positions) < 6)
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
            min_x = -FIELD_X_LENGTH / 2
        else:
            min_x = FIELD_X_LENGTH / 2 - DEFENSE_AREA_X_LENGTH
        min_y = -DEFENSE_AREA_Y_LENGTH / 2
        return np.array([min_x, min_y])

    def is_in_defense_area(self, pos, team):
        min_x, min_y = self.defense_area_corner(team)
        # defense area is a box centered at y = 0
        return ((min_x <= pos[0] <= min_x + DEFENSE_AREA_X_LENGTH) and
                min_y <= pos[1] <= min_y + DEFENSE_AREA_Y_LENGTH)

    def is_in_play(self, pos):
        return ((-FIELD_X_LENGTH / 2 <= pos[0] <= FIELD_X_LENGTH / 2) and
                (-FIELD_Y_LENGTH / 2 <= pos[1] <= FIELD_Y_LENGTH / 2))

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
    def robot_overlap(self, pos1, pos2):
        return self.overlap(pos1, pos2, ROBOT_RADIUS * 2)

    # overlap between robot and ball
    def ball_overlap(self, pos):
        ball_pos = self.get_ball_position()
        return self.overlap(pos, ball_pos, ROBOT_RADIUS + BALL_RADIUS)

    # return whether robot can be in a location without colliding another robot
    def is_position_open(self, pos):
        for key, robot_pos in self.get_all_robot_positions():
            if self.robot_overlap(pos, robot_pos).any():
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

    def get_ball_interception_point(self, team, robot_id):
        robot_pos = self.get_robot_position(team, robot_id)
        delta_t = .05
        time = 0
        while(True):
            interception_pos = self.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos - interception_pos)
            if separation_distance <= time * RobotCommands.ROBOT_MAX_SPEED:
                return interception_pos
            else:
                time += delta_t

    # return a random position inside the field
    def random_position(self):
        return (np.random.randint(0, FIELD_X_LENGTH),
                np.random.randint(0, FIELD_Y_LENGTH))

    def is_pos_valid(self, pos, team, robot_id):
        return self.is_position_open(pos) and \
            self.is_pos_in_bounds(pos, team, robot_id)

    # returns the top and bottom goalposts for a team
    def get_defense_goal(self, team):
        if (self.is_blue_defense_side_left and team == 'blue') or \
           (not self.is_blue_defense_side_left and team == 'yellow'):
            return (np.array([-FIELD_X_LENGTH / 2, GOAL_WIDTH/2]),
                    np.array([-FIELD_X_LENGTH / 2, -GOAL_WIDTH/2]))
        else:
            return (np.array([FIELD_X_LENGTH / 2, GOAL_WIDTH/2]),
                    np.array([FIELD_X_LENGTH / 2, -GOAL_WIDTH/2]))

    def get_attack_goal(self, team):
        if team == 'yellow':
            return self.get_defense_goal('blue')
        else:
            assert(team == 'blue')
            return self.get_defense_goal('yellow')

    def best_goalie_pos(self, team):
        ball_pos = self.get_ball_position()
        defense_goal = self.get_defense_goal(team)
        center_of_goal = (defense_goal[0] + defense_goal[1])/2
# The average of the two post locations will be the center of the goal.
        goal_to_ball_slope = (ball_pos[1] - center_of_goal[1])/(ball_pos[0] - center_of_goal[0])
        #return np.array([0, 0])
        best_pos = (center_of_goal + np.array[600*np.cos(np.artan(goal_to_ball_slope)), 600*np.sin(np.artan(goal_to_ball_slope)), np.arctan(goal_to_ball_slope)])
        return best_pos

    def face_pos(self, team, robot_id, pos):
        robot_pos = self.get_robot_position(team, robot_id)
        slope = (pos[1] - robot_pos[1])/(pos[0] - robot_pos[0])
# The arctan of the slope gives the angle relative to the x axis, which is the angle we would want to rotate.
        return np.arctan(slope)

    def face_ball(self, team, robot_id):
        return self.face_pos(team, robot_id, self.get_ball_position())

    def is_path_blocked(self, s_pos, g_pos):
        if not is_position_open(g_pos):
            return True
# explicitly putting this case in to avoid worrying too much about the step size in the while loop. Also it saves
# runtime if the goal position is blocked anyway. (Returning True is intended to say the path is blocked.)
        path_slope = (g_pos[1]-s_pos[1])/(g_pos[0]-s_pos[0])
        i = 1
        while (i*ROBOT_RADIUS < np.linalg.norm(g_pos - s_pos)):
            # The np expression above gives the length of the path
            if not self.is_position_open(s_pos + i*ROBOT_RADIUS*np.array[np.cos(np.arctan(path_slope)), np.sin(np.arctan(path_slope))]):
                return True
            i +=1
        return False
# Not sure if this should be switched but currently if the path is blocked we get True
