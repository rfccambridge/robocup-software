import numpy as np
import time
from typing import Iterable, Optional, List, Tuple


# Definitions + supporting logic for simple robot actions
# (have a single step/end condition, return True when done)
class Actions:
    def pivot_with_ball(self, robot_id, face_pos: Tuple[float, float]) -> bool:
        """Move robot around ball without losing possession"""
        ball_pos = self._gs.get_ball_position()
        kick_pos = self.best_kick_pos(ball_pos, face_pos)
        robot_pos = self._gs.get_robot_position(self._team, robot_id)
        # pivot gradually towards kicking position
        dw = self.wrap_pi(kick_pos[2] - robot_pos[2])
        turn_increment = dw / 3
        min_turn_increment = .05
        turn_increment += min_turn_increment / (dw / abs(dw))
        angle = robot_pos[2] + turn_increment
        waypoint = self._gs.dribbler_to_robot_pos(ball_pos, angle)
        self.set_waypoints(robot_id, [waypoint])
        remaining_error = abs(self.wrap_pi(robot_pos[2] - kick_pos[2]))
        if remaining_error < min_turn_increment and \
           self._gs.ball_in_dribbler(self._team, robot_id):
            return True
        else:
            return False

    def charge_up_to(self, robot_id, kick_speed: float) -> bool:
        """Charge kicker up to a power level that attains a specific kick_speed.
        Definition of kick speed is specified in the robot commands API/lib."""
        commands = self._gs.get_robot_commands(self._team, robot_id)
        if commands.kick_velocity() < kick_speed:
            commands.is_charging = True
        else:
            commands.is_charging = False
        return not commands.is_charging  # return whether we are done charging

    def kick_ball(self, robot_id: int):
        commands = self._gs.get_robot_commands(self._team, robot_id)
        commands.is_kicking = True

    def set_dribbler(self, robot_id: int, is_dribbling: bool) -> bool:
        commands = self._gs.get_robot_commands(self._team, robot_id)
        commands.is_dribbling = is_dribbling

    # tell specific robot to move straight towards given location
    def move_straight(self, robot_id: int, goal_pos: Tuple[float, float, float], is_urgent=False):
        self.set_waypoints(robot_id, [goal_pos], is_urgent)
        return self.is_done_moving(robot_id)

    # find a legal path for robot to go to position, returns whether arrived
    # TODO: still goes through defense area - need to fix see is_path_blocked
    def path_find(self, robot_id: int, goal_pos: Tuple[float, float, float]) -> bool:
        if not self._gs.is_pos_legal(self._gs.get_robot_position(self._team, robot_id), self._team, robot_id):
            self.move_straight(robot_id, [0, 0, None])
            return self.is_done_moving(robot_id)
        if not self._gs.is_position_open(goal_pos, self._team, robot_id):
            print("cannot path find to blocked goal")
            return False
        start_pos = self._gs.get_robot_position(self._team, robot_id)
        # always check if we can just go straight
        if not self.is_path_blocked(start_pos, goal_pos, robot_id, buffer_dist=150):
            self.move_straight(robot_id, np.array(goal_pos))
            return self.is_done_moving(robot_id)
        # now check if current waypoints are already going where we want
        current_goal = self.get_goal_pos(robot_id)
        SAME_GOAL_THRESHOLD = 100  # TODO
        is_same_goal = current_goal is not None and \
            np.linalg.norm(goal_pos[:2] - current_goal[:2]) < SAME_GOAL_THRESHOLD
            # np.array_equal(goal_pos[:2], current_goal[:2])
        commands = self._gs.get_robot_commands(self._team, robot_id)
        current_waypoints = [start_pos] + commands.waypoints
        current_path_collides = False
        for i in range(len(current_waypoints) - 1):
            wp, next_wp = current_waypoints[i], current_waypoints[i+1]
            if self.is_path_blocked(wp, next_wp, robot_id):
                current_path_collides = True
        # avoid rerunning too often so we don't crash the system
        # RRT_MIN_INTERVAL = .1
        # recently_called = robot_id in self._last_RRT_times and \
        #     time.time() - self._last_RRT_times[robot_id] < RRT_MIN_INTERVAL
        # only rerun for same goal if long time has elapsed or path collides
        MIN_REFRESH_INTERVAL = 3  # mainly in case something very strange has happened
        need_refresh = robot_id not in self._last_RRT_times or \
            time.time() - self._last_RRT_times[robot_id] > MIN_REFRESH_INTERVAL
        if (current_path_collides or not is_same_goal or need_refresh):
            self._last_RRT_times[robot_id] = time.time()
            is_success = self.RRT_path_find(start_pos, goal_pos, robot_id)
            if not is_success:
                return False
        return self.is_done_moving(robot_id)
