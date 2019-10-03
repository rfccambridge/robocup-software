import pyglet
import time
import numpy as np
import threading
from collections import deque
from vision import SSLVisionDataProvider

BALL_POS_HISTORY_LENGTH = 20
BALL_LOST_TIME = .1
ROBOT_POS_HISTORY_LENGTH = 20
ROBOT_LOST_TIME = .2

class GameState(object):
    """Game state contains all the relevant information in one place. Many
       threads can edit or use the game state at once, cuz Python GIL"""
    def __init__(self):
        # NOTE: in general fields with underscores are "private" so
        # should only be accessed through getter and setter methods

        # Raw Position Data (updated by vision data or simulator)
        self._ball_position = deque([], BALL_POS_HISTORY_LENGTH) # queue of (time, pos)        
        # robot positions are x, y, w (rotation)
        self._robot_positions = dict() # Robot ID: queue of (timestamp, position)
        # TODO: store both teams robots
        # TODO: include game states/events, such as time, score and ref events (see docs)
        
        # Commands data (desired robot actions)
        self.robot_waypoints = dict()  # Dict of current movement plans for robot_id
        self.robot_dribblers = dict()  # Dict of dribbler speeds for robot_id
        self.robot_charges = dict()  # Dict of kicker charging (bool) for robot_id
        self.robot_kicks = dict()  # Dict of kicker discharging (bool) for robot_id

        # TODO: analysis data (i.e. ball trajectory)
        self.ball_trajectory = None
        
        # gamestate thread is for doing analysis on raw data (i.e. trajectory calcuations, etc.)
        self._is_analyzing = False
        self._analysis_thread = None

    def start_analyzing(self):
        self._is_analyzing = True
        self._analysis_thread = threading.Thread(target=self.analysis_loop)
        self._analysis_thread.start()

    def analysis_loop(self):
        while self._is_analyzing:
            # TODO: calculate from the position history
            self.ball_trajectory = (1, 1)
            # yield to other threads - run this loop at most 20 times per second
            time.sleep(.05)

    def stop_analyzing(self):
        self._is_analyzing = False
        self._analysis_thread.join()
        self._analysis_thread = None

    # RAW DATA GET/SET FUNCTIONS
    # returns position ball was last seen at
    def get_ball_position(self):
        if len(self._ball_position) == 0:
            print("getting ball position but ball never seen?!?")
            return None
        timestamp, pos = self._ball_position[0]
        return pos

    def update_ball_position(self, pos):
        self._ball_position.appendleft((time.time(), pos))

    def get_ball_last_update_time(self):
        if len(self._ball_position) == 0:
            print("getting ball update time but ball never seen?!?")
            return None
        timestamp, pos = self._ball_position[0]
        return timestamp
    
    def is_ball_lost(self):
        return time.time() - self.get_ball_last_update_time() > BALL_LOST_TIME

    def get_blue_team_robot_ids(self):
        # UDPATE WHEN INCLUDE YELLOW TEAM
        return self._robot_positions.keys()
    
    # returns position robot was last seen at
    def get_robot_position(self, robot_id):
        if robot_id not in self._robot_positions:
            print("getting position of robot never seen?!?")
            return None
        timestamp, pos = self._robot_positions[robot_id][0]
        return pos
        
    def update_robot_position(self, robot_id, pos):
        if robot_id not in self._robot_positions:
            self._robot_positions[robot_id] = deque([], ROBOT_POS_HISTORY_LENGTH)
        self._robot_positions[robot_id].appendleft((time.time(), pos))
    
    def get_robot_last_update_time(self, robot_id):
        if robot_id not in self._robot_positions:
            print("getting update time of robot never seen?!?")
            return None
        timestamp, pos = self._robot_positions[robot_id][0]
        return timestamp
        
    def is_robot_lost(self, robot_id):
        return time.time() - self.get_robot_last_update_time(robot_id) > ROBOT_LOST_TIME
