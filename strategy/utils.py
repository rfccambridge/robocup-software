import numpy as np


# Strategy helper funtions for geometry + working with commands
class Utils:
    # convert angle to between -pi and pi
    def wrap_pi(self, angle):
        return (angle + np.pi) % (np.pi * 2) - np.pi

    # helper - format + insert list of waypoints into robot commands
    def set_waypoints(self, robot_id, waypoints, is_urgent=False):
        current_pos = self._gs.get_robot_position(self._team, robot_id)
        commands = self._gs.get_robot_commands(self._team, robot_id)
        # print(waypoints)
        for i, p in enumerate(waypoints):
            assert(len(p) == 2 or len(p) == 3)
            if len(p) == 2:
                waypoints[i] = np.array([p[0], p[1], None])
        commands.set_waypoints(waypoints, current_pos, is_urgent)

    # format + single waypoint into robot commands
    def append_waypoint(self, robot_id, goal_pos, is_urgent=False):
        current_pos = self._gs.get_robot_position(self._team, robot_id)
        commands = self._gs.get_robot_commands(self._team, robot_id)
        commands.append_waypoint(goal_pos, current_pos, is_urgent=False)

    # get a robot's final waypoint
    # TODO: move to gamestate?
    def get_goal_pos(self, robot_id):
        commands = self._gs.get_robot_commands(self._team, robot_id)
        if not commands.waypoints:
            return None
        return commands.waypoints[-1]

    # Check if robot has arrived at final waypoint, angle included
    def is_done_moving(self, robot_id):
        robot_pos = self._gs.get_robot_position(self._team, robot_id)
        commands = self._gs.get_robot_commands(self._team, robot_id)
        waypoints = commands.waypoints
        if waypoints:
            destination = waypoints[-1]
            delta = destination - robot_pos
            linear_delta = np.linalg.norm(delta[:2])
            LINEAR_THRESHOLD = 60
            ANGLE_THRESHOLD = .05
            return linear_delta < LINEAR_THRESHOLD and \
                abs(delta[2]) < ANGLE_THRESHOLD
        return True

    # get angle (relative to the x axis) betweeen two positions
    def face_pos(self, facing_from_pos, facing_towards_pos):
        dx, dy = facing_towards_pos[:2] - facing_from_pos[:2]
        # use atan2 instead of atan because it takes into account x/y signs
        # to give angle from -pi to pi, instead of limiting to -pi/2 to pi/2
        angle = np.arctan2(dy, dx)
        return angle

    # get angle from robot to position
    def robot_face_pos(self, robot_id, pos):
        robot_pos = self._gs.get_robot_position(self._team, robot_id)
        return self.face_pos(robot_pos, pos)

    # get angle from robot to ball
    def robot_face_ball(self, robot_id):
        return self.robot_face_pos(robot_id, self._gs.get_ball_position())
