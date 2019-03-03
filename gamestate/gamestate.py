import pyglet
import time
import numpy as np
import threading
from vision import SSLVisionDataProvider


class GameState(object):
    """We will store the game state here to have the most up to date information
	available at all times."""
    
    def __init__(self):
        self.ball = None # ball position
        self.robots = dict()  # Dict of Robot ID (int) to x, y coord (numpy)
        self.waypoints = dict()  # Dict of current trajectory plans for robot_id
        self.trajectories = dict()  # Dict of current trajectory plans for robot_id
        self._updating = False
        self._data_provider = None
        self._data_thread = None

    def update_ball(self, loc):
        """Update ball location"""
        self.ball = loc

    def update_robot(self, robot_id, loc):
        """Update location of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        loc (np.array): numpy array of size 3, in format [x_coord, y_coord, rotation]"""
        self.robots[robot_id] = loc

    def update_trajectory(self, robot_id, traj):
        """Update trajectory of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        traj (np.array): numpy array of size 2, in format [forward_direction, 
            lateral_direction (right)]"""
        self.trajectories[robot_id] = traj

    def update_waypoint(self, robot_id, waypoint):
        """Update trajectory of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        traj (np.array): numpy array of size 2, in format [forward_direction, 
            lateral_direction (right)]"""
        self.waypoints[robot_id] = waypoint

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
            # TODO: store both teams robots
            robot_positions = self._data_provider.get_robot_positions()
            for robot_id, robot_data in robot_positions.items():
                loc = robot_data
                if loc:
                    x, y, w = loc.x, loc.y, loc.orientation
                    self.update_robot(robot_id, np.array([x, y, w]))

            ball_data = self._data_provider.get_ball_position()
            if ball_data:
                ball_pos = ball_data.x, ball_data.y
                self.update_ball(ball_pos)

    def stop_updating(self):
        self._updating = False
        self._data_provider.stop()
        self._data_provider = None
        self._data_thread.join()
        self._data_thread = None

    
    

        
