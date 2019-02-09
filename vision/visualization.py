import pyglet
import time
import numpy as np
from gym.envs.classic_control import rendering
from data_providers import SSLVisionDataProvider

# The size of our current field in ROBOCUP
FIELD_W = 3200
FIELD_H = 2400
ROBOT_SIZE = 12

# Scale for the display window, or else it gets too large...
SCALE = 0.25

class GameState(object):
    """Robocup homegrown visualization library that essentially does the same
    as the modules in OpenAI gym. We will store the game state here for
    convenience, so we can choose whether or not to render all at once instead
    of when any new information gets transmitted."""
    
    def __init__(self):
        self.viewer = None
        self._robots = dict()  # Dict of Robot ID (int) to x, y coord (numpy)
        self._drawn_robot_txs = dict()  # Dict that deals with drawing robot transforms and rotations
        self._trajectories = dict()  # Dict of current trajectory plans for robot_id
        self._drawn_trajectories = dict()
        self._waypoints = dict()  # Dict of current trajectory plans for robot_id
        self._drawn_waypoints = dict()
        self.user_click = None
        self.user_click_field = None


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


    def render(self):
        if self.viewer is None:
            self.viewer = rendering.Viewer(int(FIELD_W * SCALE), int(FIELD_H * SCALE))
            a = rendering.make_circle(50)
            self.viewer.add_geom(a)
            # Traps your mouse inside the screen
            # self.viewer.window.set_exclusive_mouse(True)
            def on_mouse_press(x, y, button, modifiers):
                self.user_click = (x, y)
                self.user_click_field = int(x / SCALE), int(y / SCALE)

            self.viewer.window.on_mouse_press = on_mouse_press
            b = rendering.make_circle(50)

        print('Last button clicked: %s' % str(self.user_click))

        # Draw all of the robots as separate entities for robot_id, loc in self._robots: # If the robot hasn't been drawn yet, add it as a separate draw object. if robot_id not in self._drawn_robots:
        for robot_id, loc in self._robots.items():
            if robot_id not in self._drawn_robot_txs:
                # print("Adding a new robot into our drawn game state")
                robot_points = [
                    (ROBOT_SIZE, 0), (0, -ROBOT_SIZE), (-ROBOT_SIZE, 0),
                    (0, ROBOT_SIZE), (ROBOT_SIZE, 0), (0, 0)]
                drawn_robot = rendering.make_polyline(robot_points)
                # drawn_robot.set_linewidth(5)
                self._drawn_robot_txs[robot_id] = rendering.Transform()
                drawn_robot.add_attr(self._drawn_robot_txs[robot_id])
                
                drawn_robot.set_color(0., 0., 0.)
                self.viewer.add_geom(drawn_robot)
            
            # use the transform object to "move" the robot on-screen
            loc *= np.array([SCALE, SCALE, 1.0])
            scaled_y, scaled_x, w = loc[0], loc[1], loc[2]
            self._drawn_robot_txs[robot_id].set_translation(scaled_x, scaled_y)
            self._drawn_robot_txs[robot_id].set_rotation(np.pi / 2 - w)

            # if we have a trajectory object, we can draw that
            if robot_id in self._trajectories:
                pass
            
            if robot_id in self._waypoints:
                if robot_id not in self._drawn_waypoints:
                    waypt = rendering.make_circle(5)
                    self._drawn_waypoints[robot_id] = rendering.Transform() 
                    waypt.add_attr(self._drawn_waypoints[robot_id])
                    self.viewer.add_geom(waypt)
                
                loc = self._waypoints[robot_id]
                # Our coordinate system is brutally fucked, x and y are flipped
                # this is john's fault.
                y, x = int(loc[0] * SCALE), int(loc[1] * SCALE)
                self._drawn_waypoints[robot_id].set_translation(x, y)

    
        return self.viewer.render()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None


if __name__ == '__main__':
    data = SSLVisionDataProvider()
    data.start()
    gs = GameState()
    gs.render()

    ROBOT_ID = 9  # John's testing robot is ID 9
    while True:
        loc = data.get_robot_position(ROBOT_ID)
        if loc:
            x, y, w = loc.x, loc.y, loc.orientation
            gs.update_robot(ROBOT_ID, np.array([x, y, w]))
            gs.render()

