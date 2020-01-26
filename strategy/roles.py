import numpy as np
import sys
# import lower-level strategy logic
try:
    from actions import Actions
    from routines import Routines
except (SystemError, ImportError):
    from .actions import Actions
    from .routines import Routines


class Roles:
    """High level strategic roles and analysis"""
    # TODO: generalize for building walls and stuff
    # TODO: account for attacker orientation?
    def block_goal_center_pos(self, max_distance_from_goal, ball_pos=None, team=None):
        if team is None:
            team = self._team
        if ball_pos is None:
            ball_pos = self._gs.get_ball_position()
        if not self._gs.is_in_play(ball_pos):
            return np.array([])
        goal_top, goal_bottom = self._gs.get_defense_goal(team)
        goal_center = (goal_top + goal_bottom) / 2
        ball_distance = np.linalg.norm(ball_pos - goal_center)
        distance_from_goal = min(max_distance_from_goal, ball_distance - self._gs.ROBOT_RADIUS)
        # for now, look at vector from goal center to ball
        goal_to_ball = ball_pos - goal_center
        if not goal_to_ball.any():
            # should never happen, but good to prevent crash, and for debugging
            print('ball is exactly on goal center w0t')
            return np.array([*goal_center, 0])
        angle_to_ball = np.arctan2(goal_to_ball[1], goal_to_ball[0])
        norm_to_ball = goal_to_ball / np.linalg.norm(goal_to_ball)
        x, y = goal_center + norm_to_ball * distance_from_goal
        block_pos = np.array([x, y, angle_to_ball])
        # TODO: THIS IS A HACK TO MAKE IT STAY WITHIN CAMERA RANGE
        # if block_pos[0] > self._gs.FIELD_MAX_X - self._gs.ROBOT_RADIUS * 3 or block_pos[0] < self._gs.FIELD_MIN_X + self._gs.ROBOT_RADIUS * 3:
        #    return np.array([]) 
        return block_pos

    # get behind ball without touching it, to avoid pushing it in
    def get_behind_ball(self):
        ball_pos = self._gs.get_ball_position()

    def goalie(self, robot_id, is_opposite_goal=False):
        team = self._team
        # for demo purposes, allow playing as opposite goalie
        if is_opposite_goal:
            team = 'yellow' if team == 'blue' else 'blue'
        shot_location = self._gs.is_shot_coming(team)
        if shot_location is not None:
            # robot goes to ball using to nearest interception point
            intercept_range = self.intercept_range(robot_id)
            if intercept_range is None:
                # TODO: go to closest point in trajectory?
                # don't give up!
                intercept_pos = shot_location
            else:
                intercept_pos = intercept_range[0]
            self.move_straight(robot_id, intercept_pos, is_urgent=True)
        else:
            GOALIE_OFFSET = 600  # goalie stays this far from goal center
            goalie_pos = self.block_goal_center_pos(GOALIE_OFFSET, ball_pos=None, team=team)
            if goalie_pos.any():
                self.move_straight(robot_id, goalie_pos)
