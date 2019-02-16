import pyglet
import time
import numpy as np
import threading
from data_providers import SSLVisionDataProvider


class GameState(object):
    """Robocup homegrown visualization library that essentially does the same
    as the modules in OpenAI gym. We will store the game state here for
    convenience, so we can choose whether or not to render all at once instead
    of when any new information gets transmitted."""
    
    def __init__(self):
        self._updating = False
        self._ball = None # ball position
        self._robots = dict()  # Dict of Robot ID (int) to x, y coord (numpy)
        self._trajectories = dict()  # Dict of current trajectory plans for robot_id
        self._waypoints = dict()  # Dict of current trajectory plans for robot_id
        self._data_provider = None
        self._data_thread = None

    def update_ball(self, loc):
        """Update ball location"""
        self._ball = loc

    def update_robot(self, robot_id, loc):
        """Update location of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        loc (np.array): numpy array of size 3, in format [x_coord, y_coord, rotation]"""
        self._robots[robot_id] = loc

    def update_trajectory(self, robot_id, traj):
        """Update trajectory of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        traj (np.array): numpy array of size 2, in format [forward_direction, 
            lateral_direction (right)]"""
        self._trajectories[robot_id] = traj

    def update_waypoint(self, robot_id, waypoint):
        """Update trajectory of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        traj (np.array): numpy array of size 2, in format [forward_direction, 
            lateral_direction (right)]"""
        self._waypoints[robot_id] = waypoint

    def scale_pos(self, tup):
        return tuple([int(SCALE * n) for n in tup])

    def start_updating(self):
        if not self._data_provider:
            self._data_provider = SSLVisionDataProvider()
        self._data_provider.start()
        self._updating = True
        self._data_thread = threading.Thread(target=self.update_loop)
        self._data_thread.start()

    def update_loop(self):
        ROBOT_ID = 8  # John's testing robot is ID 9
        while self._updating:
            loc = self._data_provider.get_robot_position(ROBOT_ID)
            if loc:
                x, y, w = loc.x, loc.y, loc.orientation
                self.update_robot(ROBOT_ID, np.array([x, y, w]))

            ball_data = self._data_provider.get_ball_position()
            if ball_data:
                ball_pos = ball_data.x, ball_data.y
                self.update_ball(ball_pos)

    def stop_updating(self):
        self._updating = False
        self._data_provider.close()
        self._data_provider = None
        self._data_thread.join()
        self._data_thread = None
    

        
