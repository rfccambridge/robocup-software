import pyglet
import time
import numpy as np
import threading
from vision import SSLVisionDataProvider


class GameState(object):
    """Game state contains all the relevant information in one place. Many
       threads can edit or use the game state at once."""
    def __init__(self):
        # TODO: include game states/events, such as time, score and ref events (see docs)
        
        # Raw position data (updated from simulator
        self.ball_position = None # ball position
        self.robot_positions = dict()  # Dict of Robot ID (int) to x, y, w coord (numpy)
        # TODO: store past position data
        # TODO: store both teams robots

        # Commands data (desired robot actions)
        self.robot_waypoints = dict()  # Dict of current movement plans for robot_id
        self.robot_dribblers = dict()  # Dict of dribbler speeds for robot_id
        self.robot_charges = dict()  # Dict of kicker charging (bool) for robot_id
        self.robot_kicks = dict()  # Dict of kicker discharging (bool) for robot_id

        # TODO: analysis data (i.e. ball trajectory)
        
        # TODO: move thread to vision? make own analysis thread?
        self._updating = False
        self._data_provider = None
        self._data_thread = None

    # TODO: got rid of getter and setter functions for now, but might
    # be useful for updating history? we'll see...

    def start_updating(self):
        if not self._data_provider:
            self._data_provider = SSLVisionDataProvider()
        self._data_provider.start()
        self._updating = True
        self._data_thread = threading.Thread(target=self.update_loop)
        self._data_thread.start()

    def update_loop(self):
        while self._updating:
            # update positions of all (blue team) robots seen by data feed
            robot_positions = self._data_provider.get_robot_positions()
            for robot_id, robot_data in robot_positions.items():
                self.robot_positions[robot_id] = robot_data.x, robot_data.y, robot_data.orientation

            ball_data = self._data_provider.get_ball_position()
            if ball_data:
                self.ball_position = ball_data.x, ball_data.y

    def stop_updating(self):
        self._updating = False
        self._data_provider.stop()
        self._data_provider = None
        self._data_thread.join()
        self._data_thread = None

    def is_obstacle(self, pos):
        """ Returns whether or not a robot can pass through a point
            Obstacles should include:
            - Other robots
            - Illegal areas of the field
        """
        return False;
    
    

        
