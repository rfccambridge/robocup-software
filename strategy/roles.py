# pylint: disable=maybe-no-member
import numpy as np
from random import random
import time


class Roles:
    """High level strategic roles and analysis"""
    # get behind ball without touching it, to avoid pushing it in
    def get_behind_ball(self):
        # ball_pos = self.gs.get_ball_position()
        # TODO, and move to routines!
        raise NotImplementedError

    def random_robot(self, robot_id):
        if self.is_done_moving(robot_id):
            pos = self.gs.get_robot_position(self._team, robot_id)
            stepsize = 1000
            random_movement = np.array([(random() - 0.5) * stepsize,
                                        (random() - 0.5) * stepsize,
                                        0])
            self.move_straight(robot_id, pos + random_movement)

    def goalie(self, robot_id, is_opposite_goal=False):
        """Commands a given robot id to play as goalie"""
        team = self._team
        GOALIE_OFFSET = 600  # goalie stays this far from goal center
        # for demo purposes, allow playing as opposite goalie
        if is_opposite_goal:
            team = 'yellow' if team == 'blue' else 'blue'
        shot_location = self.gs.is_shot_coming(team)
        ball_pos = self.gs.get_ball_position()
        ball_in_defense_area = self.gs.is_in_defense_area(ball_pos, team)
        if shot_location is not None:
            # robot goes to ball using to nearest interception point
            # Note that that if the robot CAN intercept the ball, this function
            # returns the same thing as intercept_range
            intercept_pos = self.safest_intercept_point(robot_id)
            self.move_straight(robot_id, intercept_pos, is_urgent=True)  # noqa
        # reclaim the ball if it has gotten behind the goalie
        elif ball_in_defense_area and (shot_location is None):
            goal_posts = self.gs.get_defense_goal(team)
            goal_x = goal_posts[0][0]
            ball_x, ball_y = self.gs.get_ball_position()
            x, y, w = self.gs.get_robot_position(team, robot_id)
            # check which goal we're defending
            is_ball_behind = (x < ball_x < goal_x) or (x > ball_x > goal_x)
            is_avoiding_ball = (y > ball_y + self.gs.ROBOT_RADIUS) or \
                               (y < ball_y - self.gs.ROBOT_RADIUS)
            # get ball and clear it (ie kick the ball somewhere sensible)
            if self.gs.ball_in_dribbler(team, robot_id):
                self.clear_ball(robot_id)
            elif is_ball_behind and is_avoiding_ball:
                self.move_straight(robot_id, np.array([goal_x, y, w]))
            else:
                self.get_ball(robot_id)
        else:
            goalie_pos = self.block_goal_center_pos(
                GOALIE_OFFSET, ball_pos=None, team=team
            )
            if goalie_pos.any():
                self.move_straight(robot_id, goalie_pos)

    def attacker_on_ball(self, robot_id):
        """Attacker that has the ball"""
        team = self._team
        # Shooting velocity
        shoot_velocity = 1200
        goal = self.gs.get_attack_goal(team)
        center_of_goal = (goal[0] + goal[1]) / 2
        robot_pos = self.gs.get_robot_position(team, robot_id)
        # TODO: Movement and receive ball
        # Shoots if has the ball
        if self.gs.ball_in_dribbler(team, robot_id):
            if self.within_shooting_range(team, robot_id) and \
               self.is_straight_path_open(
                    robot_pos, center_of_goal,
                    ignore_ids=[robot_id],
                    buffer=0
               ):
                self.prepare_and_kick(robot_id, center_of_goal, shoot_velocity)
            else:
                team_position_data = self.gs.get_team_positions(team)
                team_posns = {}
                for id, pos_data in team_position_data.items():
                    team_posns[id] = pos_data[0][1]
                best_teammates = sorted(
                    team_posns.items(),
                    key=lambda x: self.rate_pass_pos(x[1], x[0]),
                    reverse=True
                )
                for teammate in best_teammates:
                    teammate_id, teammate_pos = teammate
                    if teammate_id == robot_id:
                        self.logger.debug(f"{robot_id} not passing")
                        break
                    # if self.rate_pass_pos(robot_pos, robot_id) \
                    #    < self.rate_pass_pos(teammate_pos, teammate_id):
                    else:
                        #    and self.is_straight_path_open(
                        #         robot_pos, teammate_pos,
                        #         ignore_ids=[robot_id, teammate_id],
                        #         buffer=0
                        #    ):
                        self.logger.debug(f"{robot_id} pass to {teammate_id}")
                        self.pass_ball(robot_id, teammate_id)
                        break
                # self.set_dribbler(robot_id, True)
                # self.set_waypoints(robot_id,
                #     [self.attacker_get_open(robot_id)])
        else:
            self.logger.debug(f"{robot_id} trying to get ball")
            ball_pos = self.gs.get_ball_position()
            if self.gs.is_pos_legal(ball_pos, team, robot_id):
                self.get_ball(robot_id, charge_during=shoot_velocity)
            else:
                new_pos = self.find_legal_pos(robot_id, ball_pos)
                self.path_find(robot_id, new_pos)

    def attacker_off_ball(self, robot_id):
        """Commands a given robot id to play as attacker without a ball"""
        MIN_REFRESH_INTERVAL = .1
        if robot_id not in self._last_pathfind_times or \
           time.time() - self._last_pathfind_times[robot_id] > MIN_REFRESH_INTERVAL:  # noqa
            pos_x, pos_y = self.attacker_get_open(robot_id)
            ball_pos = self.gs.get_ball_position()
            pos_w = self.face_pos([pos_x, pos_y], ball_pos)
            self.path_find(robot_id, [pos_x, pos_y, pos_w])
        # time.sleep(1)

    def attacker_off_ball2(self, robot_id):
        """Commands a given robot id to play as attacker without a ball"""
        MIN_REFRESH_INTERVAL = .1
        if robot_id not in self._last_pathfind_times or \
           time.time() - self._last_pathfind_times[robot_id] > MIN_REFRESH_INTERVAL:  # noqa
            pos_x, pos_y = self.attacker_get_open(robot_id)
            ball_pos = self.gs.get_ball_position()
            pos_w = self.face_pos([pos_x, pos_y], ball_pos)
            self.path_find(robot_id, [pos_x, pos_y, pos_w])

    def deep_attacker(self, robot_id):
        """Commands a given robot id to play as attacker without a ball"""
        MIN_REFRESH_INTERVAL = .1
        if robot_id not in self._last_pathfind_times or \
           time.time() - self._last_pathfind_times[robot_id] > MIN_REFRESH_INTERVAL:  # noqa
            pos_x, pos_y = self.attacker_get_open(
                robot_id,
                pos_rating=self.rate_deep_attacker_pos
            )
            ball_pos = self.gs.get_ball_position()
            pos_w = self.face_pos([pos_x, pos_y], ball_pos)
            self.path_find(robot_id, [pos_x, pos_y, pos_w])

    def free_kicker(self, robot_id):
        team = self._team
        shoot_velocity = 1200
        goal = self.gs.get_attack_goal(team)
        goalie_pos = self.get_enemy_goalie_position()
        center_of_goal = (goal[0] + goal[1]) / 2
        target = center_of_goal

        if goalie_pos[1] > center_of_goal[1]:
            target[1] = goal[1][1] + 1.5 * self.gs._BALL_RADIUS
        else:
            target[1] = goal[0][1] - 1.5 * self.gs._BALL_RADIUS
        self.prepare_and_kick(robot_id, target, shoot_velocity)

    def defender(self, robot_id):
        ball_pos = self.gs.get_ball_position()
        curr_pos = self.gs.get_robot_position(self._team, robot_id)[0:2]
        goal_top, goal_bottom = self.gs.get_defense_goal(self._team)
        goal_center = (goal_top + goal_bottom) / 2
        maxDistance = np.linalg.norm(curr_pos - goal_center)
        interceptPos = self.block_goal_center_pos(
            maxDistance, ball_pos, team=self._team
        )
        if len(interceptPos) != 0 and \
           self.gs.is_pos_legal(interceptPos, self._team, robot_id):
            distance = self.distance_from_line(goal_center, ball_pos, curr_pos)
            offense_team, _ = self.which_robot_has_ball()
            if offense_team is None:
                self.get_ball(robot_id)
            elif distance >= self.gs.ROBOT_RADIUS:
                # self.logger.debug(f"{distance}")
                # Might want to make a faster path finder to stop ball
                self.path_find(robot_id, interceptPos)
            else:
                DEFENDER_OFFSET = min(500, np.linalg.norm(curr_pos - ball_pos))
                curr_offset = np.linalg.norm(ball_pos - goal_center)
                total_offset = curr_offset - DEFENDER_OFFSET
                defender_pos = self.block_goal_center_pos(total_offset)
                self.move_straight(robot_id, defender_pos)

    def defender2(self, robot_id):
        '''
        Defender that stays back and blocks enemies that might be a threat
        '''
        threats = self.identify_enemy_threat_level_advanced(robot_id)
        if len(threats) == 0:
            return
        enemy_id = threats[0][0]
        enemy_pos = self.gs.get_robot_position(self.gs.other_team(self._team),
                                               enemy_id)
        curr_pos = self.gs.get_robot_position(self._team, robot_id)[0:2]
        goal_top, goal_bottom = self.gs.get_defense_goal(self._team)
        goal_center = (goal_top + goal_bottom) / 2
        max_distance = max(np.linalg.norm(curr_pos - goal_center), 2000)
        intercept_pos = self.block_goal_center_pos(
            max_distance, enemy_pos[:2], team=self._team
        )
        self.path_find(robot_id, intercept_pos)

    # Specialized roles (penalty taker, free kick taker, etc)

    def penalty_taker(self, robot_id):
        '''
        Prepares to take a penalty kick when the penalty command is issued
        '''
        ball_pos = self.gs.get_ball_position()
        if self.defending_on_left():
            from_ball_vector = - [1.5 * self.gs.ROBOT_RADIUS, 0]
        else:
            from_ball_vector = [1.5 * self.gs.ROBOT_RADIUS, 0]
        dest_x, dest_y = ball_pos + from_ball_vector
        dest_w = self.face_pos([dest_x, dest_y], ball_pos)
        self.path_find(robot_id, [dest_x, dest_y, dest_w])

    def penalty_goalie(self, robot_id):
        goal_top, goal_bottom = self.gs.get_defense_goal(self._team)
        goal_center = (goal_top + goal_bottom) / 2
        ball_pos = self.gs.get_ball_position()
        # Get player closest to ball for other team
        ranked_dists = self.rank_intercept_distances(other_team=True)
        penalty_kicker = ranked_dists[0][0]
        penalty_kicker_pos = self.gs.get_robot_position(
            self.gs.other_team(self._team), penalty_kicker)
        # Calculate predicted trajectory of ball with trig
        x_dist = goal_center[0] - ball_pos[0]
        y_target = x_dist * np.tan(penalty_kicker_pos[2])
        # Make sure that the goalie does not go too far to the sides
        buffer = self.gs.ROBOT_RADIUS*2
        if goal_center[1] + y_target > goal_top[1] - buffer:
            y_target = goal_top[1] - buffer - goal_center[1]
        if goal_center[1] + y_target < goal_bottom[1] + buffer:
            y_target = goal_bottom[1] + buffer - goal_center[1]
        goalie_target = [goal_center[0], goal_center[1] + y_target]
        self.move_straight(robot_id, goalie_target)

    def indirect_freekicker(self, robot_id):
        if self.gs.ball_in_dribbler(team, robot_id):
            team_position_data = self.gs.get_team_positions(team)
            team_posns = {}
            for id, pos_data in team_position_data.items():
                team_posns[id] = pos_data[0][1]
            best_teammates = sorted(
                team_posns.items(),
                key=lambda x: self.rate_pass_pos(x[1], x[0]),
                reverse=True
            )
            for teammate in best_teammates:
                teammate_id, teammate_pos = teammate
                if teammate_id == robot_id:
                    continue
                else:
                    #    and self.is_straight_path_open(
                    #         robot_pos, teammate_pos,
                    #         ignore_ids=[robot_id, teammate_id],
                    #         buffer=0
                    #    ):
                    self.logger.debug(f"{robot_id} pass to {teammate_id}")
                    self.pass_ball(robot_id, teammate_id)
                    break
        else:
            pass_velocity = 600
            self.get_ball(robot_id, charge_during = pass_velocity)
