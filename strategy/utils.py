"""Strategy helper functions for geometry + working with commands"""

import numpy as np
from typing import Tuple, List

class Utils:
    def wrap_pi(self, angle: float) -> float:
        """convert angle to between -pi and pi"""
        return (angle + np.pi) % (np.pi * 2) - np.pi

    def set_speeds(self, robot_id, x, y, w):
        commands = self.gs.get_robot_commands(self._team, robot_id)
        commands.set_speeds(x, y, w)

    def set_waypoints(self, 
        robot_id: int, 
        waypoints: List[Tuple[float, float]], 
        is_urgent: bool = False
    ) -> None:
        """format + insert list of waypoints into robot commands"""
        current_pos = self.gs.get_robot_position(self._team, robot_id)
        commands = self.gs.get_robot_commands(self._team, robot_id)
        for i, p in enumerate(waypoints):
            assert(len(p) == 2 or len(p) == 3)
            if len(p) == 2:
                waypoints[i] = np.array([p[0], p[1], None])
        commands.set_waypoints(waypoints, current_pos, is_urgent)

    def append_waypoint(self, robot_id: int, goal_pos: Tuple[float, float], is_urgent=False) -> None:
        """format + single waypoint into robot commands"""
        current_pos = self.gs.get_robot_position(self._team, robot_id)
        commands = self.gs.get_robot_commands(self._team, robot_id)
        commands.append_waypoint(goal_pos, current_pos, is_urgent=False)

    # TODO: move to gamestate?
    def get_goal_pos(self, robot_id: int) -> Tuple[float, float, float]:
        """Return a robot's final waypoint"""
        commands = self.gs.get_robot_commands(self._team, robot_id)
        if not commands.waypoints:
            return None
        return commands.waypoints[-1]

    def is_done_moving(self, robot_id: int) -> bool:
        """Check if robot has arrived at final waypoint, angle included"""
        robot_pos = self.gs.get_robot_position(self._team, robot_id)
        commands = self.gs.get_robot_commands(self._team, robot_id)
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

    def face_pos(self,
        facing_from_pos: Tuple[float, float],
        facing_towards_pos: Tuple[float, float]
    ) -> float:
        """Return angle (relative to the x axis) betweeen two positions"""
        dx, dy = facing_towards_pos[:2] - facing_from_pos[:2]
        # use atan2 instead of atan because it takes into account x/y signs
        # to give angle from -pi to pi, instead of limiting to -pi/2 to pi/2
        angle = np.arctan2(dy, dx)
        return angle

    def robot_face_pos(self, robot_id: int, pos: Tuple[float, float]):
        """Return angle from robot to position"""
        robot_pos = self.gs.get_robot_position(self._team, robot_id)
        return self.face_pos(robot_pos, pos)

    def robot_face_ball(self, robot_id: int) -> float:
        """Return angle from robot to ball"""
        return self.robot_face_pos(robot_id, self.gs.get_ball_position())
