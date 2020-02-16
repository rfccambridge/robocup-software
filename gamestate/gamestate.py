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

from multiprocessing import Queue

class GameState(object):
    """
    A GameState object synchronises the entire game. It is
    the source of truth for all game state related information
    including vision, refbox data and commands that should be 
    sent to the robot.
    """
    def __init__(self):
        self.is_playing = False
        # A queue of commands from the yellow strategy waiting to be processed
        self.yellow_commands_queue = Queue()
        # A queue of the latest gamestate waiting to be read by the yellow strategy proc
        self.yellow_gamestate_queue = Queue()
        self.yellow_strategy = Strategy('yellow', 
                                        data_in_q=self.yellow_gamestate_queue,
                                        commands_out_q=self.yellow_commands_queue)
        self.yellow_strategy_process = Process(target=self.yellow_strategy.run_strategy))
    
        self.blue_commands_queue = Queue()
        self.blue_gamestate_queue = Queue()
        self.blue_strategy = Strategy('blue', 
                                        data_in_q=self.blue_gamestate_queue,
                                        commands_out_q=self.blue_commands_queue)
        self.blue_strategy_process = Process(target=self.blue_strategy.run_strategy))

        # Commands data (desired robot actions)
        self._blue_robot_commands = dict()  # Robot ID: commands object
        self._yellow_robot_commands = dict()  # Robot ID: commands object

    def start_game(self):
        self.is_playing = True
        self.game_loop()

    def stop_game(self):
        self.is_playing = False
        self.clean_up()

    def game_loop(self):
        while self.is_playing:
            self.vision_data = self.get_updated_vision_data()
            self.refbox_data = self.get_updated_refbox_data()
            self.publish_new_gamestate()
            self.update_robot_commands()
            self.publish_robot_commands()

    def get_updated_vision_data(self):
        pass

    def get_updated_refbox_data(self):
        pass

    def publish_robot_commands(self):
        # send robot commands to xbee here
        # or to simulator
        pass

    def publish_new_gamestate(self):
        snapshot = self.snapshot_gamedata()
        try:
            self.blue_gamestate_queue.put_nowait(snapshot)
        except:
            # Likely queue is full
            pass
        try:
            self.yellow_gamestate_queue.put_nowait(snapshot)
        except:
            # Likely queue is full 
            pass
    
    def update_robot_commands(self):
        try:
            self._blue_robot_commands = self.blue_commands_queue.get_nowait()
        except:
            # Likely queue is empty
            pass
        try:
            self._yellow_robot_commands = self.yellow_commands_queue.get_nowait()
        except:
            # Likely queue is empty
            pass
        
    def snapshot_gamedata(self):
        d = {}
        d['vision_data'] = self.some_vision_data
        return d

    def clean_up(self):
        self.yellow_strategy_process.terminate()
        self.blue_strategy_process.terminate()

        

class GameFunctions(Field, Analysis):
    """Game state contains all raw game information in one place.
       Many threads can edit and use the game state at once, cuz Python GIL
       Since using python, data types are specified in the comments below.
       Fundamental physics and game rules functions are available from gamestate.
    """
    def __init__(self, game_data):
        # NOTE: Fields starting with _underscore are "private" so
        # should be accessed through getter and setter methods

        for key, val in game_data.items():
            self.__setattr__(key, val)

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
        self.refbox_msg = None
        # TODO: enum all ref box restart commands

        # UI Inputs - set from visualizer
        self.user_click_position = None
        self.user_drag_vector = None
        self.user_selected_robot = None  # (team, id) of robot
        self.user_selected_ball = False
        self.user_charge_command = False
        self.user_kick_command = False
        self.user_dribble_command = False

        # Refbox - the latest message delivered from the refbox
        self.latest_refbox_message = None

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

    def new_game_loop(self):
        # update_vision()
        # update_refbox()
        # send_new_state_to_strategy_procs()
        # update_robot_commands()
        # pipe_commands_to_xbee_process() if not simulation

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

    def other_team(self, team):
        if team == 'blue':
            return 'yellow'
        else:
            return 'blue'
    
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
