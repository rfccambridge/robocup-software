import pyglet
import time
import numpy as np
import threading
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
    as the modules in OpenAI gym."""
    
    def __init__(self, gamestate):
        self.gamestate = gamestate
        self.viewer = None
        self.user_click = None
        self.user_click_field = None

        self.transform_ball = None
        self.transform_waypoint = None
        self.transform_robots = {} 

        self._updating = False
        self._visualization_thread = None

    def scale_pos(self, tup):
        return tuple([int(SCALE * n) for n in tup])

    def start_visualizing(self):
        self._updating = True
        self._visualization_thread = threading.Thread(target=self.visualization_loop)
        self._visualization_thread.start()

    def visualization_loop(self):
        while self._updating:
            start_time = time.time()
            self.render()
            end_time = time.time()
            print("Total Render Overhead: %s s" % str(end_time - start_time))

    def stop_visualizing(self):
        self._updating = False
        self._visualization_thread.join()
        self._visualization_thread = None

    def render(self):
        start_time = time.time()
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
            drawn_ball = rendering.make_circle(BALL_SIZE)
            self.transform_ball = rendering.Transform()
            drawn_ball.add_attr(self.transform_ball)
            drawn_ball.set_color(*BALL_COLOR)
            self.viewer.add_geom(drawn_ball)

            # Waypoint
            drawn_waypoint = rendering.make_circle(WAYPOINT_SIZE)
            self.transform_waypoint = rendering.Transform()
            drawn_waypoint.add_attr(self.transform_waypoint)
            drawn_waypoint.set_color(*WAYPOINT_COLOR)
            self.viewer.add_geom(drawn_waypoint)
        # Draw the ball
        if self.gamestate._ball:
            # print(self.transform_ball)
            self.transform_ball.set_translation(*self.scale_pos(self.gamestate._ball))
        # Draw all of the robots as separate entities:
        # print(self.gamestate._robots)
        for robot_id, loc in self.gamestate._robots.items():
            # draw robot at screen-scaled location for this frame if robot has
            # not yet been drawn so far, otherwise just set the location
            # of the rendered object
            if robot_id not in self.transform_robots:
                self.transform_robots[robot_id] = rendering.Transform()
                robot_points = [(ROBOT_SIZE, 0), (0, -ROBOT_SIZE), (-ROBOT_SIZE, 0),
                                (0, ROBOT_SIZE), (ROBOT_SIZE, 0), (0, 0)]

                drawn_robot = rendering.make_polyline(robot_points)
                # drawn_robot.set_linewidth(5)
                self.transform_robots[robot_id] = rendering.Transform()
                drawn_robot.add_attr(self.transform_robots[robot_id])

                drawn_robot.set_color(*ROBOT_COLOR)
                self.viewer.add_geom(drawn_robot)           
            
            # Place the rendered robot in the correct location
            x, y, w = loc
            robot_screen_loc = self.scale_pos((x, y))
            robot_rotation = w
            self.transform_robots[robot_id].set_translation(*robot_screen_loc)
            self.transform_robots[robot_id].set_rotation(robot_rotation)

            # TODO: draw any trajectories for this robot
            if robot_id in self.gamestate._trajectories:
                pass
            
            # draw any waypoints for this robot TODO: and line from robot to it?
            if robot_id in self.gamestate._waypoints:
                waypoint_screen_loc = self.scale_pos(self.gamestate._waypoints[robot_id])
                self.transform_waypoint.set_translation(*waypoint_screen_loc)
        print("Viz prep overhead: %s s" % str(time.time() - start_time))
        return self.viewer.render()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

