import numpy as np


# Part of the Gamestate class we've separated out for readability
class Field(object):
    """Gamestate functions about the field specs
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

    # returns bottom left corner of defense area
    def defense_area_corner(self, team):
        if team == "blue" and self.is_blue_defense_side_left or \
           team == "yellow" and not self.is_blue_defense_side_left:
            min_x = self.FIELD_MIN_X
        else:
            min_x = self.FIELD_MAX_X - self.DEFENSE_AREA_X_LENGTH
        min_y = -self.DEFENSE_AREA_Y_LENGTH / 2
        return np.array([min_x, min_y])

    def is_in_defense_area(self, pos, team):
        min_x, min_y = self.defense_area_corner(team)
        # defense area is a box centered at y = 0
        return ((min_x <= pos[0] <= min_x + self.DEFENSE_AREA_X_LENGTH) and
                min_y <= pos[1] <= min_y + self.DEFENSE_AREA_Y_LENGTH)

    def is_in_play(self, pos):
        return ((self.FIELD_MIN_X <= pos[0] <= self.FIELD_MAX_X) and
                (self.FIELD_MIN_Y <= pos[1] <= self.FIELD_MAX_Y))

    def is_pos_legal(self, pos, team, robot_id):
        # TODO: during free kicks must be away from opponent area
        # + ALL OTHER RULES
        is_defender_too_close = self.is_in_defense_area(pos, team) and \
                not self.is_goalie(team, robot_id)
        return self.is_in_play(pos) and not is_defender_too_close

    # return a random position inside the field
    def random_position(self):
        return (np.random.randint(0, self.FIELD_X_LENGTH),
                np.random.randint(0, self.FIELD_Y_LENGTH))

    def is_pos_valid(self, pos, team, robot_id):
        return self.is_position_open(pos, team, robot_id) and \
            self.is_pos_in_bounds(pos, team, robot_id)

    # returns the top and bottom goalposts for a team
    def get_defense_goal(self, team):
        if (self.is_blue_defense_side_left and team == 'blue') or \
           (not self.is_blue_defense_side_left and team == 'yellow'):
            return (np.array([self.FIELD_MIN_X, self.GOAL_WIDTH/2]),
                    np.array([self.FIELD_MIN_X, -self.GOAL_WIDTH/2]))
        else:
            return (np.array([self.FIELD_MAX_X, self.GOAL_WIDTH/2]),
                    np.array([self.FIELD_MAX_X, -self.GOAL_WIDTH/2]))

    def get_attack_goal(self, team):
        if team == 'yellow':
            return self.get_defense_goal('blue')
        else:
            assert(team == 'blue')
            return self.get_defense_goal('yellow')
