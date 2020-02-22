import time
import threading
import numpy as np
from collections import deque
# import RobotCommands from the comms folder
# (expected to run from root directory, use try/except if run from here)
from comms import RobotCommands

# import parts of gamestate that we've separated out for readability
# (they are actually just part of the same class)
try:
    from field import Field
    from analysis import Analysis
except (SystemError, ImportError):
    from .field import Field
    from .analysis import Analysis

# RAW DATA PROCESSING CONSTANTS
BALL_POS_HISTORY_LENGTH = 100
BALL_LOST_TIME = .1
ROBOT_POS_HISTORY_LENGTH = 20
# time after which robot is considered lost by gamestate
ROBOT_LOST_TIME = .2
# time after which lost robot is deleted from the gamestate
ROBOT_REMOVE_TIME = 5


class GameState(Field, Analysis):
    """Game state contains all raw game information in one place.
       Many threads can edit and use the game state at once, cuz Python GIL
       Since using python, data types are specified in the comments below.
       Fundamental physics and game rules functions are available from gamestate.
    """
    def __init__(self):
        # NOTE: Fields starting with _underscore are "private" so
        # should be accessed through getter and setter methods

        # Thread keeps track of game status/events
        self._is_playing = False
        self._game_thread = None
        self._game_loop_sleep = None
        self._last_step_time = None

        # Raw Position Data - updated by vision provider (either vision or simulator)
        # queue of (time, pos) where positions are in the form np.array([x, y])
        # most recent data is at the front of queue
        self._ball_position = deque([], BALL_POS_HISTORY_LENGTH)
        # robot positions are np.array([x, y, w]) where w = rotation
        self._blue_robot_positions = dict()  # Robot ID: queue of (time, pos)
        self._yellow_robot_positions = dict()  # Robot ID: queue of (time, pos)

        # Commands Data (desired robot actions) - updated by strategy
        self._blue_robot_commands = dict()  # Robot ID: commands object
        self._yellow_robot_commands = dict()  # Robot ID: commands object

        # UI Inputs - updated by visualizer
        self.viz_inputs = {
            "user_click_position": None,
            "user_drag_vector": None,
            "user_selected_robot": None,  # (team, id) of robot
            "user_selected_ball": False,
            "user_charge_command": False,
            "user_kick_command": False,
            "user_dribble_command": False
        }
        
        # Refbox - the latest message delivered from the refbox
        # Contains all? relevant game status information such as time, events, goalie id, direction of play
        # See protocol: https://github.com/RoboCup-SSL/ssl-refbox/blob/master/referee.proto
        self.latest_refbox_message = None
        # TODO - functions to get data from refbox message?
        # Game status/events
        self.game_clock = None
        self.is_blue_defense_side_left = True

    def other_team(self, team):
        if team == 'blue':
            return 'yellow'
        else:
            return 'blue'
    
    # GAME STATUS/EVENT FUNCTIONS
    def wait_until_game_begins(self):
        pass

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

    # TODO write a "is_goalie(self, team, robot_id)" function to determine
    # whether the robot of interest is a goalie.
    def is_goalie(self, team, robot_id):
        return False

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
