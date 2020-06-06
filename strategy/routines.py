# pylint: disable=maybe-no-member
from typing import Tuple


class Routines:
    """Definitions + supporting logic for multi-step sequences of actions
    Use simple state management, return whether finished"""
    def prepare_and_kick(self, robot_id: int,
                         kick_pos: Tuple[float, float, float],
                         min_charge: float = 0) -> bool:
        """Command robot to get into position, charge to given level, & kick"""
        done_pivoting = self.pivot_with_ball(robot_id, kick_pos)
        done_charging = self.charge_up_to(robot_id, min_charge)
        if done_pivoting and done_charging:
            self.kick_ball(robot_id)
            return True
        return False

    def get_ball(self, robot_id, charge_during=0):
        """Command robot to go to the ball and start dribbling it"""
        # robot goes to ball using to nearest interception point
        intercept_range = self.intercept_range(robot_id)
        if intercept_range is None:
            return False
        intercept_xy = intercept_range[0]
        # this will do gradual turn, does it make sense?
        intercept_angle = self.robot_face_ball(robot_id)
        intercept_pos = self.gs.dribbler_to_robot_pos(
            intercept_xy,
            intercept_angle
        )
        self.set_dribbler(robot_id, True)
        self.path_find(robot_id, intercept_pos)
        # start charging up
        self.charge_up_to(robot_id, charge_during)
        # use more specific condition to check if we're done
        return self.gs.ball_in_dribbler(self._team, robot_id)

    def pass_ball(self, passer_id, receiver_id, pass_velocity=600):
        self.logger.debug(f"Robot {passer_id} attempting pass to robot {receiver_id}")
        if not self.gs.ball_in_dribbler(self._team, passer_id):
            self.get_ball(passer_id, charge_during=pass_velocity)
        if passer_id == receiver_id:
            return True
        goal_pos = self.gs.get_robot_position(self._team, receiver_id)
        pass_complete = self.prepare_and_kick(passer_id, goal_pos, min_charge=pass_velocity)
        if pass_complete:
            self.logger.debug(f"Robot {passer_id} successfully passed to robot {receiver_id}")
        return pass_complete
