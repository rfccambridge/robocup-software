

# Definitions + supporting logic for multi-step sequences of actions
# Use simple state management, return whether finished
class Routines:
    # robot gets in position, charges, then kicks
    def prepare_and_kick(self, robot_id, kick_pos, min_charge=0):
        done_pivoting = self.pivot_with_ball(robot_id, kick_pos)
        done_charging = self.charge_up_to(robot_id, min_charge)
        if done_pivoting and done_charging:
            self.kick_ball(robot_id)
            return True
        return False

    # make robot directly go get possession of the ball (asap)
    def get_ball(self, robot_id, charge_during=0):
        # robot goes to ball using to nearest interception point
        intercept_range = self.intercept_range(robot_id)
        if intercept_range is None:
            return False
        intercept_xy = intercept_range[0]
        # this will do gradual turn, does it make sense?
        intercept_angle = self.robot_face_ball(robot_id)
        intercept_pos = self._gs.dribbler_to_robot_pos(
            intercept_xy,
            intercept_angle
        )
        self.set_dribbler(robot_id, True)
        self.path_find(robot_id, intercept_pos)
        # start charging up
        self.charge_up_to(robot_id, charge_during)
        # use more specific condition to check if we're done
        return self._gs.ball_in_dribbler(self._team, robot_id)
