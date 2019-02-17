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
        self.drawn_ball = None
        self.drawn_robots = {}
        self.drawn_waypoints = {}
        self.gamestate = gamestate
        self.viewer = None
        self.user_click = None
        self.user_click_field = None

        self.transform_ball = None
        self.transform_robots = {} 


    def scale_pos(self, tup):
        return tuple([int(SCALE * n) for n in tup])
        #STOP LEV GO DO RESEARCH 
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

            # Ball object and transform.
            ball_tx = rendering.Transform()
            self.transform_ball = ball_tx
            self.viewer.draw_circle(BALL_SIZE, 20, color=BALL_COLOR).add_attr(ball_tx)

            # Robot objects and transform


        # Draw the ball
        if self.gamestate._ball:
            print(self.transform_ball)
            self.transform_ball.set_translation(self.scale_pos(self.gamestate._ball))
            self.transform_ball.set_rotation(0)

        # Draw all of the robots as separate entities:
        for robot_id, loc in self.gamestate._robots.items():
            # draw robot at screen-scaled location for this frame if robot has
            # not yet been drawn so far, otherwise just set the location
            # of the rendered object
            if robot_id not in self.transform_robots:
                self.transform_robots[robot_id] = rendering.Transform()
                robot_points = [(ROBOT_SIZE, 0), (0, -ROBOT_SIZE), (-ROBOT_SIZE, 0),
                                (0, ROBOT_SIZE), (ROBOT_SIZE, 0), (0, 0)]
                self.viewer.draw_polyline(robot_points, color=ROBOT_COLOR).add_attr(
                    self.transform_robots[robot_id])            
            
            # Place the rendered robot in the correct location
            x, y, w = loc
            robot_screen_loc = self.scale_pos((x, y))
            robot_rotation = w
            self.transform_robots[robot_id].set_translation(robot_screen_loc)
            self.transform_robots[robot_id].set_rotation(robot_rotation)

            # TODO: draw any trajectories for this robot
            if robot_id in self.gamestate._trajectories:
                pass
            
            # draw any waypoints for this robot TODO: and line from robot to it?
            """
            if robot_id in self.gamestate._waypoints:
                waypoint_screen_loc = self.scale_pos(self.gamestate._waypoints[robot_id])
                t = rendering.Transform(translation=waypoint_screen_loc)
                self.viewer.draw_circle(WAYPOINT_SIZE, color=WAYPOINT_COLOR).add_attr(t)
            """


        return self.viewer.render()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

