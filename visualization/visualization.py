import pyglet
import time
import numpy as np
import threading
from gym.envs.classic_control import rendering

# The size of the field (should match location data from ssl-vision)
FIELD_W = 9000
FIELD_H = 6000
CENTER_CIRCLE_RADIUS = 495

# rendering constants
ROBOT_SIZE = 12
ROBOT_COLOR = (0, 0, 0)

BALL_SIZE = 5
BALL_COLOR = (1, .5, 0)

WAYPOINT_SIZE = 3
WAYPOINT_COLOR = (0, 0, 0)

# Scale for the display window, or else it gets too large... (pixels/mm)
SCALE = 0.15

class Visualizer(object):
    """Robocup homegrown visualization library that essentially does the same
    as the modules in OpenAI gym."""
    
    def __init__(self, gamestate):
        self.user_click = None
        self.user_click_field = None

        self._gamestate = gamestate
        self._viewer = None
        self._transform_ball = None
        self._transform_waypoint = None
        self._transform_robots = {} 

        self._updating = False
        self._visualization_thread = None

    def scale_pos(self, tup):
        # shift position so (0, 0) becomes the center of the field, as in ssl-vision
        assert(len(tup) == 2)
        tup = (tup[0] + FIELD_W / 2, tup[1] + FIELD_H / 2)
        # scale for display
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
        if self._viewer is None:
            # for single cam, viewer window boundaries should correspond to cam
            self._viewer = rendering.Viewer(int(FIELD_W * SCALE), int(FIELD_H * SCALE))

            # draw field landmarks
            center_circle = rendering.make_circle(CENTER_CIRCLE_RADIUS * SCALE)
            circle_transform = rendering.Transform()
            circle_transform.set_translation(*self.scale_pos((0, 0)))
            center_circle.add_attr(circle_transform)
            center_circle.set_color(.9, .9, .9)
            self._viewer.add_geom(center_circle)
            hw, hh = FIELD_W / 2, FIELD_H / 2
            corner_points = [(-hw, -hh), (-hw, hh),
                             (0, hh), (0, -hh), (0, hh),
                             (hw, hh), (hw, -hh), (-hw, -hh)]
            scaled_corner_points = [self.scale_pos(p) for p in corner_points]            
            boundary_lines = rendering.make_polyline(scaled_corner_points)
            boundary_lines_transform = rendering.Transform()
            boundary_lines_transform.set_translation(*self.scale_pos((-hw, -hh)))
            boundary_lines.add_attr(boundary_lines_transform)
            boundary_lines.set_linewidth(2)
            boundary_lines.set_color(0, 0, 0)
            self._viewer.add_geom(boundary_lines)

            # Traps your mouse inside the screen
            # self.viewer.window.set_exclusive_mouse(True)
            # update user click position - coordinates flipped
            def on_mouse_press(x, y, button, modifiers):
                self.user_click = (x, y)
                self.user_click_field = int(x / SCALE), int(y / SCALE)

            self._viewer.window.on_mouse_press = on_mouse_press

            # Ball object and transform.
            drawn_ball = rendering.make_circle(BALL_SIZE)
            self._transform_ball = rendering.Transform()
            drawn_ball.add_attr(self._transform_ball)
            drawn_ball.set_color(*BALL_COLOR)
            self._viewer.add_geom(drawn_ball)

            # Waypoint
            drawn_waypoint = rendering.make_circle(WAYPOINT_SIZE)
            self._transform_waypoint = rendering.Transform()
            drawn_waypoint.add_attr(self._transform_waypoint)
            drawn_waypoint.set_color(*WAYPOINT_COLOR)
            self._viewer.add_geom(drawn_waypoint)
        # Draw the ball
        if self._gamestate.ball:
            # print(self._transform_ball)
            self._transform_ball.set_translation(*self.scale_pos(self._gamestate.ball))
        # Draw all of the robots as separate entities:
        # print(self._gamestate.robots)
        for robot_id, loc in self._gamestate.robots.items():
            # draw robot at screen-scaled location for this frame if robot has
            # not yet been drawn so far, otherwise just set the location
            # of the rendered object
            if robot_id not in self._transform_robots:
                self._transform_robots[robot_id] = rendering.Transform()
                robot_points = [(ROBOT_SIZE, 0), (0, -ROBOT_SIZE), (-ROBOT_SIZE, 0),
                                (0, ROBOT_SIZE), (ROBOT_SIZE, 0), (0, 0)]
                drawn_robot = rendering.make_polyline(robot_points)
                # drawn_robot.set_linewidth(5)
                self._transform_robots[robot_id] = rendering.Transform()
                drawn_robot.add_attr(self._transform_robots[robot_id])

                drawn_robot.set_color(*ROBOT_COLOR)
                self._viewer.add_geom(drawn_robot)           
            
            # Place the rendered robot in the correct location
            x, y, w = loc
            robot_screen_loc = self.scale_pos((x, y))
            robot_rotation = w
            self._transform_robots[robot_id].set_translation(*robot_screen_loc)
            self._transform_robots[robot_id].set_rotation(robot_rotation)

            # TODO: draw any trajectories for this robot
            if robot_id in self._gamestate.trajectories:
                pass
            
            # draw any waypoints for this robot TODO: and line from robot to it?
            if robot_id in self._gamestate.waypoints:
                waypoint_screen_loc = self.scale_pos(self._gamestate.waypoints[robot_id])
                self._transform_waypoint.set_translation(*waypoint_screen_loc)
        self._viewer.render()
        return True

    def close(self):
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None

