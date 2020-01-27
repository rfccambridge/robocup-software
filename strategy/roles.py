import numpy as np


class Roles:
    """High level strategic roles and analysis"""
    # get behind ball without touching it, to avoid pushing it in
    def get_behind_ball(self):
        ball_pos = self._gs.get_ball_position()
        # TODO, and move to routines!

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
