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
        self._trajectories = dict()  # Dict of current trajectory plans for robot_id

    def update_robot(self, robot_id, loc):
        """Update location of robot_id. Expects the following format:
        robot_id (int): ID of robot on our team for now
        loc (np.array): numpy array of size 2, in format [x_coord, y_coord]"""
        self._robots[robot_id] = loc

    def render(self):
        if self.viewer is None:
            self.viewer = rendering.Viewer(2000, 1000)

        print('render')
        if robot_coord is None:
            return
        print(robot_coord)
        self.viewer.add_geom(self.get_robot(robot_coord.x, robot_coord.y))
        self.transform = rendering.transform()
        self.viewer.render()

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
