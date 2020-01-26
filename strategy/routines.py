import numpy as np
import time

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

    # determine best robot position to kick in desired directions
    def best_kick_pos(self, from_pos, to_pos):
        dx, dy = to_pos[:2] - from_pos[:2]
        w = np.arctan2(dy, dx)
        return self._gs.dribbler_to_robot_pos(from_pos, w)

    def intercept_range(self, robot_id):
        # print(f"start time: {datetime.now()}")
        # variable at the time when the ball first gets within range.
        robot_pos = self._gs.get_robot_position(self._team, robot_id)
        delta_t = .1
        time = 0
        out_of_range = True
        while(out_of_range):
            interception_pos = self._gs.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos[:2] - interception_pos)
            max_speed = self._gs.robot_max_speed(self._team, robot_id)
            if separation_distance <= time * max_speed:
                first_intercept_point = interception_pos
                if not self._gs.is_in_play(first_intercept_point):
                    return None
                out_of_range = False
            else:
                time += delta_t
        while(not out_of_range):
            # Starting at the time when the ball first got within range.
            interception_pos = self._gs.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos[:2] - interception_pos)
            max_speed = self._gs.robot_max_speed(self._team, robot_id)
            last_intercept_point = self._gs.predict_ball_pos(time - delta_t)
            # Use opposite criteria to find the end of the window
            cant_reach = (separation_distance > time * max_speed)
            stopped_moving = (last_intercept_point == interception_pos).all()
            in_play = self._gs.is_in_play(interception_pos)
            if cant_reach or stopped_moving or not in_play:
                # we need to subtract delta_t because we found the last
                #print(f"end time: {datetime.now()}")
                return first_intercept_point, last_intercept_point
            else:
                time += delta_t

        def get_future_ball_array(self):
            ball_pos = self._gs.get_ball_position()
            # this definition of new_ball_pos guarentees that they are not the same intitally
            new_ball_pos = ball_pos - np.array([1, 1])
            time = time.time()
            delta_t = .1
            future_ball_array = []
            while (ball_pos != new_ball_pos) and is_pos_in_bounds(new_ball_pos):
                # here we make the previously generated point the reference
                ball_pos = new_ball_pos
                new_ball_pos = self._gs.predict_ball_pos()
                future_ball_array.append((new_ball_pos, time))
                time += delta_t
            return future_ball_array

        def best_failed_intercept_point(self, robot_id):
            if self.intercept_range(robot_id) is not None:
                return self.intercept_range(robot_id)
            future_ball_array = self.get_future_ball_array()
            robot_pos = self._gs.get_robot_position(robot_id)
            max_speed = self._gs.robot_max_speed(self._team, robot_id)
            time_delta = []
            for pos in future_ball_array:
                ball_time = pos[1]
                ball_pos = pos[0]
                distance_robot_needs_to_travel = np.linalg.norm(ball_pos - robot_pos)
                robot_time = distance_robot_needs_to_travel/max_speed
                time_delta.append(robot_time - ball_time)
            best_index = time_delta.index(min(time_delta))
            return future_ball_array[best_index][0]
