import numpy as np
import time
from typing import Optional, Tuple, Iterable
import logging

logger = logging.getLogger(__name__)

class Analysis(object):
    """
    The high level analysis class
    """
    def get_future_ball_array(self):
        """
        Samples incrementally to return array of future predicted ball positions
        """
        ball_pos = self.gs.get_ball_position()
        # this definition of new_ball_pos guarentees that they are not the same intitally
        new_ball_pos = ball_pos - np.array([1, 1])
        now = time.time()
        t = 0
        delta_t = .1
        future_ball_array = []
        while ((ball_pos != new_ball_pos).any() or t == 0) and self.gs.is_in_play(new_ball_pos):
            # here we make the previously generated point the reference
            ball_pos = new_ball_pos
            new_ball_pos = self.gs.predict_ball_pos(t)
            future_ball_array.append((t + now, new_ball_pos))
            t += delta_t
        return future_ball_array

    def intercept_range(self, robot_id: int
        ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """find the range for which a robot can reach the ball in its trajectory

        @return position1, position2:
            returns the positions between which robots can intercept the ball.
            returns None if interception is not possible
        """
        future_ball_array = self.get_future_ball_array()
        if len(future_ball_array) == 0:
            return None
        max_index = len(future_ball_array) - 1
        robot_pos = self.gs.get_robot_position(self._team, robot_id)
        max_speed = self.gs.robot_max_speed(self._team, robot_id)
        def buffer_time(data):
            timestamp, ball_pos = data
            ball_travel_time = timestamp - time.time()
            distance_robot_needs_to_travel = np.linalg.norm(ball_pos - robot_pos[:2])
            robot_travel_time = distance_robot_needs_to_travel / max_speed
            return ball_travel_time - robot_travel_time
        index = 0
        while(index < max_index and buffer_time(future_ball_array[index]) < 0):
            index += 1
        # This "if/elif" covers the cases when we've exhausted the future_ball_array and haven't found an last_intercept_point
        # if the last two pos entries are equal, the ball is stopped and we can get there in a time longer than the
        # scope of the array, otherwise there is no intercept pos.
        if index >= max_index:
            if (future_ball_array[max_index][1] == future_ball_array[max_index - 1][1]).all:
                return future_ball_array[max_index][1], future_ball_array[max_index][1]
            else:
                return None
        first_intercept_point = future_ball_array[index][1]
        while(index < max_index and buffer_time(future_ball_array[index]) >= 0):
            index += 1
        last_intercept_point = future_ball_array[index-1][1]
        return first_intercept_point, last_intercept_point

    def safest_intercept_point(self, robot_id: int) -> Tuple[float, float]:
        """determine the point in the ball's trajectory that the robot can reach
        soonest relative to the ball (even if it's too late)
        """
        future_ball_array = self.get_future_ball_array()
        robot_pos = self.gs.get_robot_position(self._team, robot_id)
        max_speed = self.gs.robot_max_speed(self._team, robot_id)
        def buffer_time(data):
            timestamp, ball_pos = data
            ball_travel_time = timestamp - time.time()
            distance_robot_needs_to_travel = np.linalg.norm(ball_pos - robot_pos[:2])
            robot_travel_time = distance_robot_needs_to_travel / max_speed
            return ball_travel_time - robot_travel_time
        if len(future_ball_array) > 0:
            buffer_time, safest_pos = max(future_ball_array, key=buffer_time)
        else:
            # if the ball is not visible, return current position
            safest_pos = robot_pos
        return safest_pos

    def best_kick_pos(self, from_pos: Tuple[float, float], to_pos: Tuple[float, float]) -> Tuple[float, float, float]:
        """determine the best robot position to kick in desired direction"""
        dx, dy = to_pos[:2] - from_pos[:2]
        w = np.arctan2(dy, dx)
        return self.gs.dribbler_to_robot_pos(from_pos, w)

    # TODO: generalize for building walls and stuff
    # TODO: account for attacker orientation?
    def block_goal_center_pos(self, max_distance_from_goal: float, ball_pos=None, team=None):
        """Return position between the ball and the goal, at a particular distance from the goal"""
        if team is None:
            team = self._team
        if ball_pos is None:
            ball_pos = self.gs.get_ball_position()
        if not self.gs.is_in_play(ball_pos):
            return np.array([])
        goal_top, goal_bottom = self.gs.get_defense_goal(team)
        goal_center = (goal_top + goal_bottom) / 2
        ball_distance = np.linalg.norm(ball_pos - goal_center)
        distance_from_goal = min(max_distance_from_goal, ball_distance - self.gs.ROBOT_RADIUS)
        # for now, look at vector from goal center to ball
        goal_to_ball = ball_pos - goal_center
        if not goal_to_ball.any():
            # should never happen, but good to prevent crash, and for debugging
            self.logger.exception('ball is exactly on goal center w0t')
            return np.array([*goal_center, 0])
        angle_to_ball = np.arctan2(goal_to_ball[1], goal_to_ball[0])
        norm_to_ball = goal_to_ball / np.linalg.norm(goal_to_ball)
        x, y = goal_center + norm_to_ball * distance_from_goal
        block_pos = np.array([x, y, angle_to_ball])
        # TODO: THIS IS A HACK TO MAKE IT STAY WITHIN CAMERA RANGE
        # if block_pos[0] > self.gs.FIELD_MAX_X - self.gs.ROBOT_RADIUS * 3 or block_pos[0] < self.gs.FIELD_MIN_X + self.gs.ROBOT_RADIUS * 3:
        #    return np.array([])
#        if self.gs.is_pos_valid(interceptPos, team, robot_id)
        return block_pos

    # finds a legal position for robot to move to
    def find_legal_pos(self, robot_id: int, position=None, perpendicular=False) -> Tuple[float, float, float]:
        """Returns a nearby legal and open position by searching around the robot.
        Searches perpendicular to the path to the goal first if perpendicular is set to True.
        Returns the current position if it is legal.
        """
        if position is not None and perpendicular:
            position = position[:2]
            path = position - self.gs.get_robot_position(self._team, robot_id)[:2]
            norm_path = path / np.linalg.norm(path)
            STEP_SIZE = self.gs.ROBOT_RADIUS
            direction = np.array([norm_path[1], -norm_path[0]])
            for i in range(0, 2000, int(STEP_SIZE)):
                if self.gs.is_pos_legal(position + i * direction, self._team, robot_id) and \
                   self.gs.is_position_open(position + i * direction, self._team, robot_id):
                    return position + i * direction
                if self.gs.is_pos_legal(position - i * direction, self._team, robot_id) and \
                   self.gs.is_position_open(position - i * direction, self._team, robot_id):
                    return position - i * direction
            self.logger.debug("No legal perpeudicular position found")
        if position is None:
            position = self.gs.get_robot_position(self._team, robot_id)
        if len(position) == 2:
            position = (position[0], position[1], None)
        x, y, w = position
        delta = 0
        for delta in range(0, 1000, 10):
            positions_to_try = [
                np.array([x, y + delta, w]),
                np.array([x, y - delta, w]),
                np.array([x + delta, y, w]),
                np.array([x - delta, y, w]),
                np.array([x + delta, y + delta, w]),
                np.array([x - delta, y + delta, w]),
                np.array([x + delta, y - delta, w]),
                np.array([x - delta, y - delta, w])
            ]
            for pos in positions_to_try:
                if self.gs.is_pos_legal(pos, self._team, robot_id) and \
                   self.gs.is_position_open(pos, self._team, robot_id):
                    return pos
        self.logger.debug("No legal position found open")
        return np.array([0, 0, 0])

    # Function that scores how good a position is for the attacker to get open for a pass
    # Higher ratings should indicate better positions
    def rate_attacker_pos(self, pos: Tuple[float, float, float], robot_id: int) -> float:
        ball_pos = self.gs.get_ball_position()
        if not self.gs.is_pos_legal(pos, self._team, robot_id) \
            or not self.gs.is_position_open(pos, self._team, robot_id):
            return np.NINF
        # TODO: Handle cases where path is blocked
        if not self.is_straight_path_open(ball_pos, pos):
            return np.NINF
        # Calculate the passing distance
        pass_dist = np.linalg.norm(ball_pos - pos[:2])
        # Calculate the distance to the center of the goal
        goal = self.gs.get_attack_goal(self._team)
        center_of_goal = (goal[0] + goal[1]) / 2
        goal_dist = np.linalg.norm(center_of_goal - pos[:2])
        # Calculate the proximity to opposing robots
        nearest_opponent_dist: float = self.gs.FIELD_X_LENGTH + self.gs.FIELD_Y_LENGTH
        for opponent in self.gs.get_robot_ids(self.gs.other_team(self._team)):
            opponent_pos = self.gs.get_robot_position(self.gs.other_team(self._team), opponent)
            opponent_dist: float = np.linalg.norm(opponent_pos[:2] - pos[:2])
            nearest_opponent_dist = min(nearest_opponent_dist, opponent_dist)
        # Rate the position based on metrics
        # TODO: come up with a better metric to use
        pass_wt = -1
        goal_wt = -3
        oppt_wt = 2
        # also consider off-centeredness
        goal_offctr = abs((pos[1] - center_of_goal[1]) / (pos[0] - center_of_goal[0]))
        offctr_wt = -50
        return (pass_wt * pass_dist + goal_wt * goal_dist + oppt_wt * nearest_opponent_dist + offctr_wt * goal_offctr)

    def attacker_get_open(self, robot_id : int) -> Tuple[float, float, float]:
        """Sends the attacker to a locally optimal position."""
        STEP_SIZE = 300
        offsets = [-2 * STEP_SIZE, -STEP_SIZE, 0, STEP_SIZE, 2 * STEP_SIZE]
        robot_x, robot_y, _ = self.gs.get_robot_position(self._team, robot_id)
        test_posns = [(robot_x + dx, robot_y + dy) for dx in offsets for dy in offsets]
        return max(test_posns, key=lambda p : self.rate_attacker_pos(p, robot_id))
    
    def find_attacker_pos(self, robot_id: int) -> Tuple[float, float, float]:
        """ Finds a position for attacker to get open if the ball is outside shooting range.
        To be deprecated soon; use attacker_get_open(self, robot_id) instead.
        """
        best_pos = self.gs.get_robot_position(self._team, robot_id)
        best_rating = self.rate_attacker_pos(best_pos, robot_id)
        ball_x, ball_y = self.gs.get_ball_position()
        RANGE = 1500
        STEP_SIZE = 300
        x = ball_x - RANGE
        while x <= ball_x + RANGE:
            y = ball_y - RANGE
            while y <= ball_y + RANGE:
                new_pos = [x, y, None]
                new_rating = self.rate_attacker_pos(new_pos, robot_id)
                if new_rating > best_rating:
                    best_pos = new_pos
                    best_rating = new_rating
                y += STEP_SIZE
            x += STEP_SIZE
        return best_pos

    # TODO: speed up first_path_obstacle and is_path_blocked using approach of is_straight_path_open
    def first_path_obstacle(self, s_pos, g_pos, robot_id, buffer_dist=0, allow_illegal=False):
        "finds first obstacle in a linear robot trajectory"
        s_pos = np.array(s_pos)[:2]
        g_pos = np.array(g_pos)[:2]

        if (g_pos == s_pos).all():
            return None
        
        def legal(pos):
            return self.gs.is_pos_legal(pos, self._team, robot_id) or allow_illegal
        path = g_pos - s_pos
        norm_path = path / np.linalg.norm(path)
        STEP_SIZE = self.gs.ROBOT_RADIUS
        
        # step along the path and look for a blocked point
        steps = int(np.floor(np.linalg.norm(path) / STEP_SIZE))
        for i in range(1, steps + 1):
            intermediate_pos = s_pos + norm_path * STEP_SIZE * i
            np.append(intermediate_pos, 0)
            if not self.gs.is_position_open(intermediate_pos, self._team, robot_id, buffer_dist) or not legal(intermediate_pos):
                return intermediate_pos
        return None
    
    def is_path_blocked(self, s_pos, g_pos, robot_id, buffer_dist=0, allow_illegal=False):
        "incrementally check a linear path for obstacles"
        s_pos = np.array(s_pos)[:2]
        g_pos = np.array(g_pos)[:2]

        if (g_pos == s_pos).all():
            return False
        # Check endpoint first to avoid worrying about step size in the loop
        def legal(pos):
            return self.gs.is_pos_legal(pos, self._team, robot_id) or allow_illegal
        if not self.gs.is_position_open(g_pos, self._team, robot_id) or not legal(g_pos):
            return True
        # path = g_pos - s_pos
        # norm_path = path / np.linalg.norm(path)
        # STEP_SIZE = self.gs.ROBOT_RADIUS

        return self.first_path_obstacle(s_pos, g_pos, robot_id, buffer_dist=buffer_dist, allow_illegal=allow_illegal) is not None
        
        # step along the path and check if any points are blocked
        # self.logger.info(s_pos)
        # self.logger.info(g_pos)
        # self.logger.info(path)
        # steps = int(np.floor(np.linalg.norm(path) / STEP_SIZE))
        # for i in range(1, steps + 1):
        #     intermediate_pos = s_pos + norm_path * STEP_SIZE * i
        #     np.append(intermediate_pos, 0)
        #     # self.logger.info('Legal? {}'.format(legal(intermediate_pos)))
        #     if not self.gs.is_position_open(intermediate_pos, self._team, robot_id, buffer_dist) or not legal(intermediate_pos):
        #         return True
        # return False

    def is_straight_path_open(self, s_pos, g_pos):
        """ Checks if a straight path is open, without worrying about whether it is legal for robots.
        Should be used when finding a path to send the ball.
        """
        robot_positions = self.gs.get_all_robot_positions()
        s_pos = s_pos[:2]
        g_pos = g_pos[:2]
        if (s_pos == g_pos).all():
            return True
        x1, y1 = s_pos[:2]
        x2, y2 = g_pos[:2]
        line_unit_vector = (s_pos - g_pos) / np.linalg.norm(s_pos - g_pos)
        for pos in robot_positions:
            pos = pos[1][:2]
            self.logger.debug(f"{pos}")
            x3, y3 = pos[:2]
            if np.dot(line_unit_vector, (s_pos - pos)) > 0 and \
            np.dot(line_unit_vector, (pos - g_pos)) > -1 * self.gs.ROBOT_RADIUS:
                distance_from_line = abs((-(y2-y1)*x3 + (x2-x1)*y3 - y1*(x2-x1) + x1*(y2-y1))/np.linalg.norm(g_pos-s_pos))
                if distance_from_line < 2 * self.gs.ROBOT_RADIUS:
                    return False
        return True

    def within_shooting_range(self, team, robot_id):
        # shooting range
        shoot_range = 2000
        # get center goal and robot positions
        goal = self.gs.get_attack_goal(team)
        center_of_goal = (goal[0] + goal[1]) / 2
        robot_pos = self.gs.get_robot_position(team, robot_id)[:2]
        return np.linalg.norm(robot_pos - center_of_goal) < shoot_range


    # generate RRT waypoints
    def RRT_path_find(self, start_pos, goal_pos, robot_id, lim=1000, allow_illegal = False):
        goal_pos = np.array(goal_pos)
        start_pos = np.array(start_pos)
        graph = {tuple(start_pos): []}
        prev = {tuple(start_pos): None}
        cnt = 0
        success = False
        for _ in range(lim):
            # use gamestate.random_position()
            new_pos = np.array(
                [np.random.randint(self.gs.FIELD_MIN_X, self.gs.FIELD_MAX_X),
                 np.random.randint(self.gs.FIELD_MIN_Y, self.gs.FIELD_MAX_Y),
                 0.0])
            if np.random.random() < 0.05:
                new_pos = goal_pos

            if not self.gs.is_position_open(new_pos, self._team, robot_id, buffer_dist=0) \
               or tuple(new_pos) in graph:
                continue

            nearest_pos = self.get_nearest_pos(graph, tuple(new_pos))
            extend_pos = self.extend(nearest_pos, new_pos, robot_id=robot_id)
            if extend_pos is None:
                continue

            graph[tuple(extend_pos)] = [nearest_pos]
            graph[nearest_pos].append(tuple(extend_pos))
            prev[tuple(extend_pos)] = nearest_pos

            if np.linalg.norm(extend_pos[:2] - goal_pos[:2]) < self.gs.ROBOT_RADIUS:
                success = True
                break

            cnt += 1

        if not success:
            self.logger.debug("RRT path find failing")
            return success

        pos = self.get_nearest_pos(graph, goal_pos)  # get nearest position to goal in graph
        path = []
        while not (pos[:2] == start_pos[:2]).all():
            path.append(pos)
            pos = prev[pos]
        path.reverse()

        # Smooth path to reduce zig zagging
        i = 0
        while i < len(path) - 2:
            if not self.is_path_blocked(path[i], path[i+2], robot_id, allow_illegal=allow_illegal):
                del path[i+1]
                continue
            i += 1

        # Cut out the "dead-weight" waypoints
        for i, pos in enumerate(path):
            if not self.is_path_blocked(pos, goal_pos, robot_id, allow_illegal=allow_illegal):
                path = path[:i+1]
                break

        self.set_waypoints(robot_id, path + [goal_pos])
        return success

    # RRT helper
    def get_nearest_pos(self, graph, new_pos):
        rtn = None
        min_dist = float('inf')
        for pos in graph:
            dist = np.sqrt((new_pos[0] - pos[0]) ** 2 + (new_pos[1] - pos[1]) ** 2)
            if dist < min_dist:
                min_dist = dist
                rtn = pos
        return rtn

    # RRT helper
    def extend(self, s_pos, g_pos, robot_id=None):
        s_pos = np.array(s_pos)[:2]
        g_pos = np.array(g_pos)[:2]

        if (g_pos == s_pos).all():
            return False

        path = g_pos - s_pos
        norm_path = path / np.linalg.norm(path)
        STEP_SIZE = self.gs.ROBOT_RADIUS

        # step along the path and check if any points are blocked
        poses = [None]
        steps = int(np.floor(np.linalg.norm(path) / STEP_SIZE))
        for i in range(1, steps + 1):
            intermediate_pos = s_pos + norm_path * STEP_SIZE * i
            np.append(intermediate_pos, 0)
            if not self.gs.is_position_open(intermediate_pos, self._team, robot_id, buffer_dist=100) or \
               not self.gs.is_pos_legal(g_pos, self._team, robot_id):
                break
            if np.linalg.norm(intermediate_pos - s_pos) > 4 * STEP_SIZE:
                break
            poses.append(intermediate_pos)

        return poses[-1]

    def greedy_path_find(self, start_pos, goal_pos, robot_id, lim=10, allow_illegal = False):
        """Heuristic path finder
        """
        s_pos = start_pos[:2]
        g_pos = goal_pos[:2]
        for _ in range(lim):
            # find first blocked position
            obstacle = self.first_path_obstacle(s_pos, g_pos, robot_id, buffer_dist=0, allow_illegal=allow_illegal)
            if obstacle is None:
                self.set_waypoints(robot_id, [g_pos, goal_pos])
                return True
            # find a new position if there is an obstacle
            g_pos = self.find_legal_pos(robot_id, obstacle, perpendicular=True) # TODO: make this account for allow_illegal
        return False
        
    
    def which_enemy_has_ball(self):
        BUFFER = 2 * self.gs._BALL_RADIUS
        our_team = self._team
        other_team = self.gs.other_team(our_team)
        robot_ids = self.gs.get_robot_ids(other_team)
        ball_pos = get.gs.get_ball_position()
        for id in robot_ids:
            if ball_in_dribbler(other_team, id):
                return id
        return None


    def indentify_enemy_threat_level(self):
        our_team = self._team
        other_team = self.gs.other_team(our_team)
        enemy_robot_ids = self.gs.get_robot_ids(other_team)
        enemy_robot_distances = []
        goal_top, goal_bottom = self.gs.get_defense_goal(self._team)
        goal_center = (goal_top + goal_bottom) / 2
        for id in enemy_robot_ids:
            distance = np.linalg.norm(self.gs.get_robot_position(id) - goal_center)
            enemy_robot_distances.append((id, distance))
        threats = enemy_robot_distances.sort(key = sortSecond)
        return threats
