import pyglet
import time
import numpy as np
import threading
from vision import SSLVisionDataProvider

ROBOT_LOST_TIME = .2

class GameState(object):
    """Game state contains all the relevant information in one place. Many
       threads can edit or use the game state at once."""
    def __init__(self):
        # TODO: include game states/events, such as time, score and ref events (see docs)
        
        # Raw position data (updated from simulator
        self.ball_position = None # ball position
        self.robot_positions = dict()  # Dict of Robot ID (int) to x, y, w coord (numpy)
        self.robot_last_update_times = dict()  # Dict of Robot ID (int) to time
        # TODO: store past position data
        # TODO: store both teams robots

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

    # TODO: got rid of getter and setter functions for now, but might
    # be useful for updating history? we'll see...

    def start_analyzing(self):
        self._is_analyzing = True
        self._analysis_thread = threading.Thread(target=self.analysis_loop)
        self._analysis_thread.start()

    def analysis_loop(self):
        while self._is_analyzing:
            # TODO: calculate from the position history
            self.ball_trajectory = (1, 1)

    def stop_analyzing(self):
        self._is_analyzing = False
        self._analysis_thread.join()
        self._analysis_thread = None

    def update_robot_position(self, robot_id, loc):
        self.robot_positions[robot_id] = loc
        self.robot_last_update_times[robot_id] = time.time()

    def is_robot_lost(self, robot_id):
        if robot_id not in self.robot_last_update_times:
            return True
        return time.time() - self.robot_last_update_times[robot_id] > ROBOT_LOST_TIME
