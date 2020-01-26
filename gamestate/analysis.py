import numpy as np


# Part of the Gamestate class we've separated out for readability
class Analysis(object):
    """Fundamental analysis functions for gamestate that are shared between
       simulator and strategy - think physics stuff.
    """
    BALL_RADIUS = 21 * 1.5
    ROBOT_RADIUS = 90 * 1.5  # in most cases model robot as circle
    # front of robot is actually flatter - use this for dribbling logic
    ROBOT_DRIBBLER_RADIUS = 80
    ROBOT_FRONT_ANGLE = np.arccos(ROBOT_DRIBBLER_RADIUS / ROBOT_RADIUS)
    # PHYSICS CONSTANTS
    # ball constant slowdown due to friction
    BALL_DECCELERATION = 350  # mm/s^2

    # returns the amount of overlap between circles as (x, y) vector
    def overlap(self, pos1, pos2, radius_sum):
        delta = pos2[:2] - pos1[:2]
        if not delta.any():
            return np.array([radius_sum, 0])
        distance = np.linalg.norm(delta)
        if distance <= radius_sum:
            touching_delta = delta / distance * radius_sum
            return touching_delta - delta
        return np.array([0, 0])

    # overlap between two robots
    def robot_overlap(self, pos1, pos2, buffer_dist=0):
        return self.overlap(pos1, pos2, self.ROBOT_RADIUS * 2 + buffer_dist)

    # if position is in front face of robot
    def is_robot_front_sector(self, robot_pos, pos):
        dx, dy = pos[:2] - robot_pos[:2]
        angle = np.arctan2(dy, dx)
        dw = angle - robot_pos[2]
        return np.cos(dw) * self.ROBOT_RADIUS > self.ROBOT_DRIBBLER_RADIUS

    # overlap between robot and ball
    def robot_ball_overlap(self, robot_pos, ball_pos=None):
        if ball_pos is None:
            ball_pos = self.get_ball_position()
        # account for flat front of robot in this case
        delta = ball_pos - robot_pos[:2]
        dx, dy = delta
        dw = np.arctan2(dy, dx) - robot_pos[2]
        if self.is_robot_front_sector(robot_pos, ball_pos):
            # we are in the front sector, so use linear displacement
            robot_dx = np.linalg.norm(delta) * np.cos(dw)
            overlap = self.ROBOT_DRIBBLER_RADIUS + self.BALL_RADIUS - robot_dx
            overlap = max(0, overlap)
            w = robot_pos[2]
            return np.array([overlap * np.cos(w), overlap * np.sin(w)])
        return self.overlap(robot_pos, ball_pos, self.ROBOT_RADIUS + self.BALL_RADIUS)

    # overlap of position and ball
    def ball_overlap(self, pos):
        ball_pos = self.get_ball_position()
        return self.overlap(pos, ball_pos, self.BALL_RADIUS)

    # returns the x, y position in center of robot's dribbler
    def dribbler_pos(self, team, robot_id):
        x, y, w = self.get_robot_position(team, robot_id)
        direction = np.array([np.cos(w), np.sin(w)])
        relative_pos = direction * (self.ROBOT_DRIBBLER_RADIUS + self.BALL_RADIUS)
        return np.array([x, y]) + relative_pos

    def dribbler_to_robot_pos(self, dribbler_pos, robot_w):
        direction = np.array([np.cos(robot_w), np.sin(robot_w)])
        # divide radius by 2 to go a bit closer to the ball to help make contact
        x, y = dribbler_pos - direction * (self.ROBOT_DRIBBLER_RADIUS + self.BALL_RADIUS / 2)
        return np.array([x, y, robot_w])

    # if ball is in position to be dribbled
    def ball_in_dribbler_single_frame(self, team, robot_id, ball_pos=None):
        if ball_pos is None:
            ball_pos = self.get_ball_position()
        robot_pos = self.get_robot_position(team, robot_id)
        ideal_pos = self.dribbler_pos(team, robot_id)
        # print("id {}, ball {} want {}".format(robot_id, ball_pos, ideal_pos))
        # TODO: kicking version of this function incorporates breakbeam sensor?
        MAX_DIST = self.ROBOT_RADIUS + 32  # fairly lenient constants,
        DRIBBLE_ZONE_RADIUS = 60
        in_zone = np.linalg.norm(ball_pos - ideal_pos) < DRIBBLE_ZONE_RADIUS
        close_enough = np.linalg.norm(ball_pos - robot_pos[:2]) < MAX_DIST
        #print(close_enough)
        return in_zone and close_enough

    def ball_in_dribbler(self, team, robot_id):
        positions = self._ball_position
        MIN_TIME_INTERVAL = 1
        i = 0
        if len(positions) <= 1:
            return False
        if not self.ball_in_dribbler_single_frame(team, robot_id, positions[0][1]):
            return False
        # look back from 0 (most recent) until big enough interval
        while i < len(positions) - 1 and \
              positions[0][0] - positions[i][0] < MIN_TIME_INTERVAL:
            ball_pos = positions[i][1]
            i += 1
            if not self.ball_in_dribbler_single_frame(team, robot_id, ball_pos):
                return False
        return True

    # return whether robot can be in a location without colliding another robot
    def is_position_open(self, pos, team, robot_id, buffer_dist=0):
        for key, robot_pos in self.get_all_robot_positions():
            if key == (team, robot_id):
                continue
            if self.robot_overlap(pos, robot_pos, buffer_dist).any():
                return False
        return True

    # return robot team and id occupying a current position, if any
    def robot_at_position(self, pos):
        for (team, robot_id), robot_pos in self.get_all_robot_positions():
            if self.overlap(pos, robot_pos, self.ROBOT_RADIUS).any():
                return (team, robot_id)
        return None

    # Here we find ball velocity at most recent timestamp from position data
    def get_ball_velocity(self):
        # TOOD: smooth out this value by averaging?
        # prev_velocity = self.ball_velocity
        positions = self._ball_position
        MIN_TIME_INTERVAL = .05
        i = 0
        if len(positions) <= 1:
            return np.array([0, 0])
        # look back from 0 (most recent) until big enough interval
        while i < len(positions) - 1 and \
              positions[0][0] - positions[i][0] < MIN_TIME_INTERVAL:
            i += 1
        # use those two points as reference for calculation
        time1, pos1 = positions[i]
        time2, pos2 = positions[0]
        delta_pos = pos2 - pos1
        delta_time = time2 - time1
        midpoint_velocity = delta_pos / delta_time
        if not midpoint_velocity.any():
            return np.array([0, 0])
        # print("before adjust: {}".format(midpoint_velocity))

        # adjust ball's deceleration since the midpoint of interval used
        midpoint_time = (time1 + time2) / 2
        time_since_midpoint = time2 - midpoint_time
        accel_direction = -midpoint_velocity / np.linalg.norm(midpoint_velocity)
        accel = accel_direction * self.BALL_DECCELERATION * time_since_midpoint
        velocity_now = midpoint_velocity + accel
        # truncate if slowdown has caused change directions
        if ((velocity_now * midpoint_velocity) < 0).any():
            assert(((velocity_now * midpoint_velocity) <= 0).all())
            velocity_now = np.array([0, 0])
        # print("after adjust: {}".format(velocity_now))
        return velocity_now

    def predict_ball_pos(self, delta_time):
        velocity_initial = self.get_ball_velocity()
        # print(f"{velocity_initial}")
        if not velocity_initial.any():
            return (self.get_ball_position())
        accel_direction = -velocity_initial / np.linalg.norm(velocity_initial)
        accel = accel_direction * self.BALL_DECCELERATION
        # truncate if we're going past the time where the ball would stop
        velocity_final = accel * delta_time + velocity_initial
        if ((velocity_initial * velocity_final) < 0).any():
            assert(((velocity_initial * velocity_final) <= 0).all())
# We need to use two cases here because one coordinate of initial velocity can be zero which
# would cause us to divide by zero if we use that axis.
            if not accel[0] == 0:
                time_to_stop = -1 * velocity_initial[0] / accel[0]
            else:
                time_to_stop = -1 * velocity_initial[1] / accel[1]
            # print("dt: {} TTS: {}".format(delta_time, time_to_stop))
            delta_time = time_to_stop
        predicted_pos_change = \
            0.5 * accel * delta_time ** 2 + velocity_initial * delta_time
        # print("dt: {} PPC: {}".format(delta_time, predicted_pos_change))
        predicted_pos = predicted_pos_change + self.get_ball_position()
        return predicted_pos

    # TODO: move to strategy analysis
    # return where in goal ball is going to if it is going in
    def is_shot_coming(self, team):
        start_ball_pos = self.get_ball_position()
        start_x = start_ball_pos[0]
        start_y = start_ball_pos[1]
        final_ball_pos = self.predict_ball_pos(10)
        final_x = final_ball_pos[0]
        final_y = final_ball_pos[1]
        defense_goal = self.get_defense_goal(team)
        x_pos_of_goal = defense_goal[0][0]
        GOAL_WIDTH_BUFFER = 250 # assumes shots slightly wide are going in
        GOAL_X_BUFFER = 500 # assumes shots stopping slightly short are going in
        x1 = x_pos_of_goal + GOAL_X_BUFFER
        x2 = x_pos_of_goal - GOAL_X_BUFFER
        if (min(final_x, start_x) <= x1 <= max(final_x, start_x)) or \
           (min(final_x, start_x) <= x2 <= max(final_x, start_x)):
            slope = (start_y - final_y)/(start_x - final_x)
            y_intercept = slope * (x_pos_of_goal - start_x) + start_y
            if -self.GOAL_WIDTH/2 - GOAL_WIDTH_BUFFER <= y_intercept <= self.GOAL_WIDTH/2 + GOAL_WIDTH_BUFFER:
                return np.array([x_pos_of_goal, y_intercept])
        return None
