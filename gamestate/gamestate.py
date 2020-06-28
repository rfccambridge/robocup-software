import time
import numpy as np
from collections import deque

# import RobotCommands from the comms folder
# (expected to run from root directory, use try/except if run from here)
from comms import RobotCommands, RobotStatus  # pylint: disable=import-error
from refbox import SSL_Referee  # pylint: disable=import-error

# import parts of gamestate that we've separated out for readability
# (they are actually just part of the same class)
try:
    from gamestate_field import Field
    from gamestate_analysis import Analysis
except (SystemError, ImportError):
    from .gamestate_field import Field
    from .gamestate_analysis import Analysis

# RAW DATA PROCESSING CONSTANTS
BALL_POS_HISTORY_LENGTH = 200
BALL_LOST_TIME = .15
ROBOT_POS_HISTORY_LENGTH = 20
# time after which robot is considered lost by gamestate
ROBOT_LOST_TIME = .5
# time after which lost robot is deleted from the gamestate
ROBOT_REMOVE_TIME = 5


class GameState(Field, Analysis):
    """Game state contains all raw game information in one place.
       Many threads can edit and use the game state at once, cuz Python GIL
       Since using python, data types are specified in the comments below.
       Fundamental physics and game rules functions available from gamestate.
    """
    def __init__(self):
        # NOTE: Fields starting with _underscore are "private" so
        # should be accessed through getter and setter methods

        # Thread keeps track of game status/events
        self._is_playing = False
        self._game_thread = None
        self._game_loop_sleep = None
        self._last_step_time = None

        # Raw Position Data - updated by vision provider
        # (either vision or simulator)
        # queue of (time, pos) where positions are in the form np.array([x, y])
        # most recent data is at the front of queue
        self._ball_position = deque([], BALL_POS_HISTORY_LENGTH)
        # robot positions are np.array([x, y, w]) where w = rotation
        self._blue_robot_positions = dict()  # Robot ID: queue of (time, pos)
        self._yellow_robot_positions = dict()  # Robot ID: queue of (time, pos)

        # Commands Data (desired robot actions) - updated by strategy
        self._blue_robot_commands = dict()  # Robot ID: commands object
        self._yellow_robot_commands = dict()  # Robot ID: commands object

        # Status Info (robot sensory feedback) - update by comms/sim?
        self._blue_robot_status = dict()  # Robot ID: status object
        self._yellow_robot_status = dict()  # Robot ID: status object

        # UI Inputs - updated by visualizer
        self.viz_inputs = {
            "simulator_events_count": 0,  # flag for simulator to handle
            "user_click_position": None,
            "user_drag_vector": None,
            # either ball or a robot can be selected
            "user_selected_ball": False,
            "user_selected_robot": None,  # (team, id) of robot
            # independent booleans, relevant if robot selected
            "user_charge_command": False,
            "user_kick_command": False,
            "user_dribble_command": False,
            # tell simulator to move selected robot instantly
            "teleport_selected_robot": False
        }

        # Refbox - the latest message delivered from the refbox
        # Contains all? relevant game status information such as time, events,
        # goalie id, direction of play
        # See protocol:
        # https://github.com/RoboCup-SSL/ssl-refbox/blob/master/referee.proto

        # DO NOT ACCESS THIS DIRECTLY -----
        # CALL self.get_latest_refbox_message()
        # Initialize to a default message for when we do not care
        # about the refbox
        self._latest_refbox_message_string = b'\x08\x8f\xbb\xb7\x83\x86\xf5\xe7\x02\x10\r \x00(\x010\x9e\xb6\xe3\x9b\x82\xf5\xe7\x02:\x12\n\x00\x10\x00\x18\x00(\x000\x048\x80\xc6\x86\x8f\x01@\x00B\x12\n\x00\x10\x00\x18\x00(\x000\x048\x80\xc6\x86\x8f\x01@\x00P\x00'  # noqa
        # TODO - functions to get data from refbox message?
        # Game status/events
        self.game_clock = None

    def other_team(self, team):
        if team == 'blue':
            return 'yellow'
        else:
            return 'blue'

    # helper for parsing info stored in refbox message
    def get_team_info(self, team):
        if team == 'blue':
            return self.get_latest_refbox_message().blue
        else:
            return self.get_latest_refbox_message().yellow

    def get_goalie_id(self, team):
        return self.get_team_info(team).goalie

    def is_goalie(self, team, robot_id):
        return robot_id == self.get_goalie_id(team)

    def is_blue_defense_side_left(self):
        return not self.get_latest_refbox_message().blueTeamOnPositiveHalf

    # RAW DATA GET/SET FUNCTIONS
    # returns latest refbox message
    def get_latest_refbox_message(self):
        """
        Returns latest refbox message as an object.
        See referee.proto for specifications.
        """
        if self._latest_refbox_message_string is None:
            raise Exception("Refbox message must be populated")
        refbox_message = SSL_Referee()
        refbox_message.ParseFromString(self._latest_refbox_message_string)
        # print(f"{self._latest_refbox_message_string}\n")
        return refbox_message

    def update_latest_refbox_message(self, message):
        self._latest_refbox_message_string = message

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
        self.logger.debug("This doesn't work currently")
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
        if robot_id in team_commands:
            del team_commands[robot_id]
        team_status = self.get_team_status(team)
        if robot_id in team_status:
            del team_status[robot_id]

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

    def get_team_status(self, team):
        if team == 'blue':
            return self._blue_robot_status
        else:
            assert(team == 'yellow')
            return self._yellow_robot_status

    def get_robot_commands(self, team, robot_id):
        team_commands = self.get_team_commands(team)
        if robot_id not in team_commands:
            team_commands[robot_id] = RobotCommands()
        return team_commands[robot_id]

    def get_robot_status(self, team, robot_id):
        team_status = self.get_team_status(team)
        if robot_id not in team_status:
            team_status[robot_id] = RobotStatus()
        return team_status[robot_id]

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
