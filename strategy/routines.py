import numpy as np

# import lower level strategy logic
try:
    from actions import Actions
except (SystemError, ImportError):
    from .actions import Actions

# Chained sequences of actions that have some small-scale state management

class Routines:
    # Deprecated for intercept range?
    def get_ball_interception_point(self, robot_id):
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        delta_t = .05
        time = 0
        while(True):
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos[:2] - interception_pos)
            max_speed = self._gamestate.robot_max_speed(self._team, robot_id)
            if separation_distance <= time * max_speed:
                return interception_pos
            else:
                time += delta_t

    # determine best robot position to kick in desired directions
    def best_kick_pos(self, from_pos, to_pos):
        dx, dy = to_pos[:2] - from_pos[:2]
        w = np.arctan2(dy, dx)
        return self._gamestate.dribbler_to_robot_pos(from_pos, w)

    def intercept_range(self, robot_id):
        # print(f"start time: {datetime.now()}")
        # variable at the time when the ball first gets within range.
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        delta_t = .1
        time = 0
        out_of_range = True
        while(out_of_range):
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos[:2] - interception_pos)
            max_speed = self._gamestate.robot_max_speed(self._team, robot_id)
            if separation_distance <= time * max_speed:
                first_intercept_point = interception_pos
                if not self._gamestate.is_in_play(first_intercept_point):
                    return None
                out_of_range = False
            else:
                time += delta_t
        while(not out_of_range):
            # Note that time is starting at the time when the ball first got within range.
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos[:2] - interception_pos)
            max_speed = self._gamestate.robot_max_speed(self._team, robot_id)
            last_intercept_point = self._gamestate.predict_ball_pos(time - delta_t)
            # We have the opposite criteria to find the end of the window than the beginning.
            cant_reach = (separation_distance > time * max_speed)
            stopped_moving = (last_intercept_point == interception_pos).all()
            in_play = self._gamestate.is_in_play(interception_pos)
            if cant_reach or stopped_moving or not in_play:
                # we need to subtract delta_t because we found the last
                #print(f"end time: {datetime.now()}")
                return first_intercept_point, last_intercept_point
            else:
                time += delta_t
