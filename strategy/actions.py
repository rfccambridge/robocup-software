import numpy as np
import time
import sys
# import gamestate file to use field dimension constants
# (as opposed to importing the class GameState)
sys.path.append('..')
from gamestate import gamestate as gs


# Definitions + supporting logic for simple robot actions
# (have a single step/end condition, return True when done)
class Actions:
    # helper - convert to between -pi and pi
    def wrap_pi(self, angle):
        return (angle + np.pi) % (np.pi * 2) - np.pi

    # move robot around ball without losing possession
    def pivot_with_ball(self, robot_id, face_pos):
        ball_pos = self._gamestate.get_ball_position()
        kick_pos = self.best_kick_pos(ball_pos, face_pos)
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        # pivot gradually towards kicking position
        dw = self.wrap_pi(kick_pos[2] - robot_pos[2])
        turn_increment = dw / 3
        min_turn_increment = .05
        turn_increment += min_turn_increment / (dw / abs(dw))
        angle = robot_pos[2] + turn_increment
        waypoint = self._gamestate.dribbler_to_robot_pos(ball_pos, angle)
        self.set_waypoints(robot_id, [waypoint])
        remaining_error = abs(self.wrap_pi(robot_pos[2] - kick_pos[2]))
        if remaining_error < min_turn_increment and \
           self._gamestate.ball_in_dribbler(self._team, robot_id):
            return True
        else:
            return False

    # helper - get a robot's final waypoint
    # TODO: move to gamestate? are helpers in general cluttering/confusing?
    def get_goal_pos(self, robot_id):
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        if not commands.waypoints:
            return None
        return commands.waypoints[-1]

    def charge_up_to(self, robot_id, kick_speed):
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        if commands.kick_velocity() < kick_speed:
            commands.is_charging = True
        else:
            commands.is_charging = False
        return not commands.is_charging  # return whether we are done charging

    def kick_ball(self, robot_id):
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.is_kicking = True

    def set_dribbler(self, robot_id, is_dribbling):
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.is_dribbling = is_dribbling

    # helper - check if robot has arrived at final waypoint, angle included
    def is_done_moving(self, robot_id):
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
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

    # tell specific robot to move straight towards given location
    def move_straight(self, robot_id, goal_pos):
        self.set_waypoints(robot_id, [goal_pos])
        return self.is_done_moving(robot_id)

    # helper - format + insert list of waypoints into robot commands
    def set_waypoints(self, robot_id, waypoints):
        current_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        # print(waypoints)
        for i, p in enumerate(waypoints):
            assert(len(p) == 2 or len(p) == 3)
            if len(p) == 2:
                waypoints[i] = np.array([p[0], p[1], None])
        commands.set_waypoints(waypoints, current_pos)

    # helper - format + single waypoint into robot commands
    def append_waypoint(self, robot_id, goal_pos):
        current_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.append_waypoint(goal_pos, current_pos)

    # helper - get angle (relative to the x axis) betweeen two positions
    def face_pos(self, facing_from_pos, facing_towards_pos):
        dx, dy = facing_towards_pos[:2] - facing_from_pos[:2]
        # use atan2 instead of atan because it takes into account x/y signs
        # to give angle from -pi to pi, instead of limiting to -pi/2 to pi/2
        angle = np.arctan2(dy, dx)
        return angle

    # helper - get angle from robot to position
    def robot_face_pos(self, robot_id, pos):
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        return self.face_pos(robot_pos, pos)

    # helper - get angle from robot to ball
    def robot_face_ball(self, robot_id):
        return self.robot_face_pos(robot_id, self._gamestate.get_ball_position())

    # helper - incrementally check a linear path
    def is_path_blocked(self, s_pos, g_pos, robot_id, buffer_dist=50):
        s_pos = np.array(s_pos)[:2]
        g_pos = np.array(g_pos)[:2]

        if (g_pos == s_pos).all():
            return False
        # Check endpoint first to avoid worrying about step size in the loop
        if not self._gamestate.is_position_open(g_pos, self._team, robot_id):
            return True
        path = g_pos - s_pos
        norm_path = path / np.linalg.norm(path)
        STEP_SIZE = gs.ROBOT_RADIUS

        # step along the path and check if any points are blocked
        steps = int(np.floor(np.linalg.norm(path) / STEP_SIZE))
        for i in range(1, steps + 1):
            intermediate_pos = s_pos + norm_path * STEP_SIZE * i
            np.append(intermediate_pos, 0)
            if not self._gamestate.is_position_open(intermediate_pos, self._team, robot_id):
                return True
        return False

    # find a legal path for robot to go to position, returns whether arrived
    def path_find(self, robot_id, goal_pos):
        if not self._gamestate.is_position_open(goal_pos, self._team, robot_id):
            print("cannot path find to blocked goal")
            return False
        start_pos = self._gamestate.get_robot_position(self._team, robot_id)
        # always check if we can just go straight
        if not self.is_path_blocked(start_pos, goal_pos, robot_id, buffer_dist=150):
            self.move_straight(robot_id, np.array(goal_pos))
            return self.is_done_moving(robot_id)
        # now check if current waypoints are already going where we want
        current_goal = self.get_goal_pos(robot_id)
        is_same_goal = current_goal is not None and \
            np.array_equal(goal_pos[:2], current_goal[:2])
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        current_waypoints = [start_pos] + commands.waypoints
        current_path_collides = False
        for i in range(len(current_waypoints) - 1):
            wp, next_wp = current_waypoints[i], current_waypoints[i+1]
            if self.is_path_blocked(wp, next_wp, robot_id):
                current_path_collides = True
        # only rerun for same goal if long time has elapsed or path collides
        RRT_INTERVAL = 3  # mainly in case something very strange has happened
        recently_called = robot_id in self._last_RRT_times and \
            time.time() - self._last_RRT_times[robot_id] < RRT_INTERVAL
        if current_path_collides or not is_same_goal or not recently_called:
            self._last_RRT_times[robot_id] = time.time()
            self.RRT_path_find(start_pos, goal_pos, robot_id)
        return self.is_done_moving(robot_id)

    # heper - generate RRT waypoints
    def RRT_path_find(self, start_pos, goal_pos, robot_id, lim=1000):
        goal_pos = np.array(goal_pos)
        start_pos = np.array(start_pos)
        graph = {tuple(start_pos): []}
        prev = {tuple(start_pos): None}
        cnt = 0
        while True:
            # use gamestate.random_position()
            new_pos = np.array(
                [np.random.randint(gs.FIELD_MIN_X, gs.FIELD_MAX_X),
                 np.random.randint(gs.FIELD_MIN_Y, gs.FIELD_MAX_Y),
                 0.0])
            if np.random.random() < 0.05:
                new_pos = goal_pos
                
            if not self._gamestate.is_position_open(new_pos, self._team, robot_id, buffer_dist=100) \
               or tuple(new_pos) in graph:
                continue

            nearest_pos = self.get_nearest_pos(graph, tuple(new_pos))
            extend_pos = self.extend(nearest_pos, new_pos, robot_id=robot_id)
            if extend_pos is None:
                continue

            graph[tuple(extend_pos)] = [nearest_pos]
            graph[nearest_pos].append(tuple(extend_pos))
            prev[tuple(extend_pos)] = nearest_pos

            if np.linalg.norm(extend_pos[:2] - goal_pos[:2]) < gs.ROBOT_RADIUS:
                break

            cnt += 1

        pos = self.get_nearest_pos(graph, goal_pos)  # get nearest position to goal in graph
        path = []
        while not (pos[:2] == start_pos[:2]).all():
            path.append(pos)
            pos = prev[pos]
        path.reverse()
        self.set_waypoints(robot_id, path + [goal_pos])

    def get_nearest_pos(self, graph, new_pos):
        rtn = None
        min_dist = float('inf')
        for pos in graph:
            dist = np.sqrt((new_pos[0] - pos[0]) ** 2 + (new_pos[1] - pos[1]) ** 2)
            if dist < min_dist:
                min_dist = dist
                rtn = pos
        return rtn

    def extend(self, s_pos, g_pos, robot_id=None):
        s_pos = np.array(s_pos)[:2]
        g_pos = np.array(g_pos)[:2]
        
        if (g_pos == s_pos).all():
            return False
        
        path = g_pos - s_pos
        norm_path = path / np.linalg.norm(path)
        STEP_SIZE = gs.ROBOT_RADIUS
        
        # step along the path and check if any points are blocked
        poses = [None]
        steps = int(np.floor(np.linalg.norm(path) / STEP_SIZE))
        for i in range(1, steps + 1):
            intermediate_pos = s_pos + norm_path * STEP_SIZE * i
            np.append(intermediate_pos, 0)
            if not self._gamestate.is_position_open(intermediate_pos, self._team, robot_id):
                break
            if np.linalg.norm(intermediate_pos - s_pos) > 4 * STEP_SIZE:
                break
            poses.append(intermediate_pos)
            
        return poses[-1]
