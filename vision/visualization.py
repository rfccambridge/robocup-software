import pyglet
import time
import numpy as np
from gym.envs.classic_control import rendering

# The size of our current field in ROBOCUP
FIELD_W = 3200
FIELD_H = 2400

# rendering constants
ROBOT_SIZE = 12
ROBOT_COLOR = (0, 0, 0)

BALL_SIZE = 5
BALL_COLOR = (1, .5, 0)

WAYPOINT_SIZE = 3
WAYPOINT_COLOR = (0, 0, 0)

# Scale for the display window, or else it gets too large...
SCALE = 0.25

class Visualizer(object):
    """Robocup homegrown visualization library that essentially does the same
    as the modules in OpenAI gym. We will store the game state here for
    convenience, so we can choose whether or not to render all at once instead
    of when any new information gets transmitted."""
    
    def __init__(self, gamestate):
        self.gamestate = gamestate
        self.viewer = None
        self.user_click = None
        self.user_click_field = None

    def scale_pos(self, tup):
        return tuple([int(SCALE * n) for n in tup])

    def render(self):
        if self.viewer is None:
            # for single cam, viewer window boundaries should correspond to cam
            self.viewer = rendering.Viewer(int(FIELD_W * SCALE), int(FIELD_H * SCALE))

            # Traps your mouse inside the screen
            # self.viewer.window.set_exclusive_mouse(True)
            # update user click position - coordinates flipped
            def on_mouse_press(x, y, button, modifiers):
                self.user_click = (x, y)
                self.user_click_field = int(x / SCALE), int(y / SCALE)

            self.viewer.window.on_mouse_press = on_mouse_press

        # print('Last button clicked: %s' % str(self.user_click))

        # Draw the ball
        if self.gamestate._ball:
            ball_screen_loc = self.scale_pos(self.gamestate._ball)
            t = rendering.Transform(translation=ball_screen_loc)
            self.viewer.draw_circle(BALL_SIZE, 20, color=BALL_COLOR).add_attr(t)

        # Draw all of the robots as separate entities:
        for robot_id, loc in self.gamestate._robots.items():
            # draw robot at screen-scaled location for this frame
            robot_points = [
                (ROBOT_SIZE, 0), (0, -ROBOT_SIZE), (-ROBOT_SIZE, 0),
                (0, ROBOT_SIZE), (ROBOT_SIZE, 0), (0, 0)
            ]
            x, y, w = loc
            robot_screen_loc = self.scale_pos((x, y))
            robot_rotation = np.pi / 2 - w
            t = rendering.Transform(translation=robot_screen_loc, rotation=robot_rotation)
            self.viewer.draw_polyline(robot_points, color=ROBOT_COLOR).add_attr(t)

            # TODO: draw any trajectories for this robot
            if robot_id in self.gamestate._trajectories:
                pass
            
            # draw any waypoints for this robot TODO: and line from robot to it?
            if robot_id in self.gamestate._waypoints:
                waypoint_screen_loc = self.scale_pos(self.gamestate._waypoints[robot_id])
                t = rendering.Transform(translation=waypoint_screen_loc)
                self.viewer.draw_circle(WAYPOINT_SIZE, color=WAYPOINT_COLOR).add_attr(t)
    
        return self.viewer.render()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

