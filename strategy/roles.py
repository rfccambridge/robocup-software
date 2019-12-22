import numpy as np

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
    def best_goalie_pos(self):
        ball_pos = self._gamestate.get_ball_position()
        goal_top, goal_bottom = self._gamestate.get_defense_goal(self._team)
        goal_center = (goal_top + goal_bottom) / 2
        # for now, look at vector from goal center to ball
        goal_to_ball = ball_pos - goal_center
        if not goal_to_ball.any():
            # should never happen, but good to prevent crash, and for debugging
            print('ball is exactly on goal center w0t')
            return np.array([*goal_center, 0])
        angle_to_ball = np.arctan2(goal_to_ball[1], goal_to_ball[0])
        norm_to_ball = goal_to_ball / np.linalg.norm(goal_to_ball)
        GOALIE_OFFSET = 600  # goalie stays this far from goal center
        x, y = goal_center + norm_to_ball * GOALIE_OFFSET
        best_pos = np.array([x, y, angle_to_ball])
        return best_pos

    def goalie(self, robot_id):
        goalie_pos = self.best_goalie_pos()
        self.move_straight(robot_id, goalie_pos)
