# pylint: disable=maybe-no-member
import numpy as np
from random import random

class Roles:
    """High level strategic roles and analysis"""
    # get behind ball without touching it, to avoid pushing it in
    def get_behind_ball(self):
        ball_pos = self.gs.get_ball_position()
        # TODO, and move to routines!

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
        if shot_location is not None:
            # robot goes to ball using to nearest interception point
            # Note that that if the robot CAN intercept the ball, this function
            # returns the same thing as intercept_range
            safest_intercept_point = self.safest_intercept_point(robot_id)
            self.move_straight(robot_id, safest_intercept_point, is_urgent=True)
        elif self.gs.is_in_defense_area(self.gs.get_ball_position(), team) and (shot_location is None):
            goal_posts_pos = self.gs.get_defense_goal(team)
            ball_pos_x, ball_pos_y = self.gs.get_ball_position()
            goalie_x, goalie_y, goalie_w = self.gs.get_robot_position(team, robot_id)
            # we have two cases below so that this function works regardless which goal we're defending
            if (goalie_x < ball_pos_x < goal_posts_pos[0][0]) or (goalie_x > ball_pos_x > goal_posts_pos[0][0]):
                if  (goalie_y > ball_pos_y + self.gs.ROBOT_RADIUS) or (goalie_y < ball_pos_y - self.gs.ROBOT_RADIUS):
                    self.move_straight(robot_id, np.array([goal_posts_pos[0][0], goalie_y, goalie_w]))
            self.get_ball(robot_id)
            #TODO clear ball (ie kick the ball somewhere sensible)
        else:
            goalie_pos = self.block_goal_center_pos(GOALIE_OFFSET, ball_pos=None, team=team)
            if goalie_pos.any():
                self.move_straight(robot_id, goalie_pos)

    def attacker_on_ball(self, robot_id):
        """Attacker that has the ball"""
        team = self._team
        # Shooting velocity
        shoot_velocity = 1200
        goal = self.gs.get_attack_goal(team)
        center_of_goal = (goal[0] + goal[1]) / 2
        # TODO: Movement and receive ball
        # Shoots if has the ball
        if self.gs.ball_in_dribbler(team, robot_id):
            if self.within_shooting_range(team, robot_id):
                self.prepare_and_kick(robot_id, center_of_goal, shoot_velocity)
            else:
                for teammate_id in self.gs.get_robot_ids(team):
                    if teammate_id == robot_id:
                        continue
                    this_robot_pos = self.gs.get_robot_position(team, robot_id)
                    teammate_pos = self.gs.dribbler_pos(team, teammate_id)
                    if self.is_straight_path_open(this_robot_pos, teammate_pos, ignore_ids=[robot_id, teammate_id]):
                        self.pass_ball(robot_id, teammate_id)
                        break
        else:
            ball_pos = self.gs.get_ball_position()
            if self.gs.is_pos_legal(ball_pos, team, robot_id):
                self.get_ball(robot_id, charge_during=shoot_velocity)
            else:
                self.path_find(robot_id, self.find_legal_pos(robot_id, self.gs.get_ball_position()))
    
    def attacker_off_ball(self, robot_id):
        """Commands a given robot id to play as attacker without a ball"""
        self.path_find(robot_id, self.attacker_get_open(robot_id))

    def defender(self, robot_id):
        ball_pos = self.gs.get_ball_position()
        curr_pos = self.gs.get_robot_position(self._team, robot_id)[0:2]
        goal_top, goal_bottom = self.gs.get_defense_goal(self._team)
        goal_center = (goal_top + goal_bottom) / 2
        maxDistance = np.linalg.norm(curr_pos - goal_center)
        interceptPos = self.block_goal_center_pos(maxDistance, ball_pos, team=self._team)
        if len(interceptPos) != 0 and self.gs.is_pos_legal(interceptPos, self._team, robot_id):
            distance = self.distance_from_line(goal_center, ball_pos, curr_pos)
            if distance >= self.gs.ROBOT_RADIUS:
            #     self.logger.debug(f"{distance}")
                self.move_straight(robot_id, interceptPos)
            else:
                DEFENDER_OFFSET = min(500, np.linalg.norm(curr_pos - ball_pos))
                curr_offset = np.linalg.norm(ball_pos - goal_center)
                defender_pos = self.block_goal_center_pos(curr_offset - DEFENDER_OFFSET)
                self.move_straight(robot_id, defender_pos)
