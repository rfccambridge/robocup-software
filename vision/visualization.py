import pyglet
import time
from gym.envs.classic_control import rendering
from data_providers import SSLVisionDataProvider

# The size of our current field in ROBOCUP
FIELD_W = 3200
FIELD_H = 2400

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

    def update_robot(self, robot_id, loc):
        """Update location of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        loc (np.array): numpy array of size 2, in format [x_coord, y_coord]"""
        self._robots[robot_id] = loc

    def update_trajectory(self, robot_id, traj):
        """Update trajectory of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        traj (np.array): numpy array of size 2, in format [forward_direction, 
            lateral_direction (right)]"""
        self._trajectories[robot_id] = traj

    def render(self):
        if self.viewer is None:
            self.viewer = rendering.Viewer(FIELD_W * SCALE, FIELD_H * SCALE)

        # Draw all of the robots as separate entities for robot_id, loc in self._robots: # If the robot hasn't been drawn yet, add it as a separate draw object. if robot_id not in self._drawn_robots:
        for robot_id, loc in self._robots:
            if robot_id not in self._drawn_robot_txs:
                print("Adding a new robot into our drawn game state")
                drawn_robot = rendering.FilledPolygon([(-5, 0), (0, 5), (5, 0), (0, -5)])
                self._drawn_robot_txs[robot_id] = rendering.Transform()
                drawn_robot.add_attr(self._drawn_robot_txs[robot_id])
                self.viewer.add_geom(drawn_robot)
            
            # use the transform object to "move" the robot on-screen
            scaled_x, scaled_y = loc * SCALE
            self._drawn_robot_txs[robot_id].set_translation(scaled_x, scaled_y)
            self._drawn_robot_txs[robot_id].set_translation(scaled_x, scaled_y)

            # if we have a trajectory object, we can draw that
            if robot_id in self._trajectories:
                pass
    
        return self.viewer.render()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None


if __name__ == '__main__':
    data = SSLVisionDataProvider()
    data.start()
    gs = GameState()
    
    ROBOT_ID = 9  # John's testing robot is ID 9
    for _ in range(100):
        loc = data.get_robot_position(ROBOT_ID)
        x, y = loc.x, loc.y
        gs.update_robot(ROBOT_ID, np.array([x, y]))
        gs.render()
