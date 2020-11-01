# pylint: disable=no-member
import numpy as np
from refbox import SSL_Referee  # pylint: disable=import-error


class Field(object):
    """
    Part of the Gamestate class we've separated out for readability
    """
    # FIELD + ROBOT DIMENSIONS (mm)
    FIELD_SCALE = 1  # useful if using a miniature field
    FIELD_X_LENGTH = 9000 * FIELD_SCALE
    FIELD_Y_LENGTH = 6000 * FIELD_SCALE
    FIELD_MIN_X = -FIELD_X_LENGTH / 2
    FIELD_MAX_X = FIELD_X_LENGTH / 2
    FIELD_MIN_Y = -FIELD_Y_LENGTH / 2
    FIELD_MAX_Y = FIELD_Y_LENGTH / 2
    CENTER_CIRCLE_RADIUS = 495 * FIELD_SCALE
    GOAL_WIDTH = 1000 * FIELD_SCALE
    DEFENSE_AREA_X_LENGTH = 1000 * FIELD_SCALE
    DEFENSE_AREA_Y_LENGTH = 2000 * FIELD_SCALE

    def defense_area_corner(self, team):
        """
        returns bottom left corner of defense area
        """
        if team == "blue" and self.is_blue_defense_side_left() or \
           team == "yellow" and not self.is_blue_defense_side_left():
            min_x = self.FIELD_MIN_X
        else:
            min_x = self.FIELD_MAX_X - self.DEFENSE_AREA_X_LENGTH
        min_y = -self.DEFENSE_AREA_Y_LENGTH / 2
        return np.array([min_x, min_y])

    def is_in_defense_area(self, pos, team):
        min_x, min_y = self.defense_area_corner(team)
        # account for buffer of robot radius
        radius = self.ROBOT_RADIUS
        # defense area is a box centered at y = 0
        dx_min, dy_min = min_x - radius, min_y - radius
        dx_max = min_x + self.DEFENSE_AREA_X_LENGTH + radius
        dy_max = min_y + self.DEFENSE_AREA_Y_LENGTH + radius
        in_x = dx_min <= pos[0] <= dx_max
        in_y = dy_min <= pos[1] <= dy_max
        return in_x and in_y

    def is_in_field(self, pos):
        return ((self.FIELD_MIN_X <= pos[0] <= self.FIELD_MAX_X) and
                (self.FIELD_MIN_Y <= pos[1] <= self.FIELD_MAX_Y))

    def is_pos_legal(self, pos, team, robot_id):
        # TODO: account for robot radius
        # TODO: during free kicks must be away from opponent area
        # + ALL OTHER RULES
        latest_refbox_message = self.get_latest_refbox_message()
        # TODO: Also avoid ball during other team ball placement,
        # defend free kick, etc.
        if latest_refbox_message.command == SSL_Referee.STOP:
            dist = np.linalg.norm(pos[:2] - self.get_ball_position())
            if dist <= 500 + self.ROBOT_RADIUS:
                return False
        if latest_refbox_message.command == SSL_Referee.PREPARE_PENALTY_BLUE:
            penalty_range = 1000
            if self.is_goalie(team, robot_id):
                pass
            if self.is_blue_defense_side_left():
                ball_x, _ = self.get_ball_position()
                if pos[0] < ball_x + penalty_range:
                    return False
            else:
                ball_x, _ = self.get_ball_position()
                if pos[0] > ball_x - penalty_range:
                    return False
        in_d_area = self.is_in_defense_area(pos, team)
        ot = self.other_team(team)
        in_own_defense_area = in_d_area and not self.is_goalie(team, robot_id)
        in_other_defense_area = self.is_in_defense_area(pos, ot)
        return (self.is_in_field(pos) and
                not in_own_defense_area and
                not in_other_defense_area)

    def random_position(self):
        """
        return a random position inside the field
        """
        return (np.random.randint(0, self.FIELD_X_LENGTH),
                np.random.randint(0, self.FIELD_Y_LENGTH))

    def is_pos_valid(self, pos, team, robot_id):
        return self.is_position_open(pos, team, robot_id) and \
            self.is_pos_legal(pos, team, robot_id)

    # returns the top and bottom goalposts for a team
    def get_defense_goal(self, team):
        if (self.is_blue_defense_side_left() and team == 'blue') or \
           (not self.is_blue_defense_side_left() and team == 'yellow'):
            top_post = np.array([self.FIELD_MIN_X, self.GOAL_WIDTH/2])
            bottom_post = np.array([self.FIELD_MIN_X, -self.GOAL_WIDTH/2])
            return (top_post, bottom_post)
        else:
            top_post = np.array([self.FIELD_MAX_X, self.GOAL_WIDTH/2])
            bottom_post = np.array([self.FIELD_MAX_X, -self.GOAL_WIDTH/2])
            return (top_post, bottom_post)

    def get_attack_goal(self, team):
        if team == 'yellow':
            return self.get_defense_goal('blue')
        else:
            assert team == 'blue'
            return self.get_defense_goal('yellow')
