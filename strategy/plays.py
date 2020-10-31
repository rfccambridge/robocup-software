# pylint: disable=maybe-no-member
import numpy as np


class Plays:
    """Full team role assignment for specific game cases. Used for very common
    plays that are called frequently no matter the game strategy."""

    def kickoff(self):
        '''
        Preparation for kickoff instructions
        '''
        # we tell robot 0 to follow our goalie function from roles.py
        self.goalie(1)

        # TODO: tell other robots to go to starting lineup
        # TODO: below code needs to be tested
        # ids = self.gs.get_robot_ids(self._team)
        # self.goalie(ids[0])

        # goal_top, _ = self.gs.get_defense_goal(self._team)
        # goal_x = goal_top[0]
        # circle_radius = self.gs.CENTER_CIRCLE_RADIUS

        # # position depends on whether team is on left or right
        # if goal_x == self.gs.FIELD_MIN_X:
        #     attacker_x = - 1 * circle_radius
        # else:
        #     attacker_x = circle_radius

        # # kick off positions (ordered by 'priority'):
        # #   attacker in the center, defender slightly up,
        # #   defender slightly down, attacker slightly up,
        # #   attacker slightly down
        # # if < 6 robots, their positions are deterimined by 'priority'
        # kickoff_pos = [
        #     (attacker_x, 0),
        #     (goal_x / 2, circle_radius),
        #     (goal_x / 2, -1 * circle_radius),
        #     (attacker_x, self.gs.FIELD_MAX_Y / 2),
        #     (attacker_x, self.gs.FIELD_MIN_Y / 2)
        # ]

        # for i in range(1, len(ids)):
        #     self.move_straight(ids[i], kickoff_pos[i])

    def reset_game(self):
        raise NotImplementedError

    def halt(self):
        for robot_id in self.gs.get_robot_ids(self._team):
            self.stop(robot_id)

    def avoid_ball(self, robot_ids=None, distance=500,
                   speed_limit=1500):
        """Specified (all by default) robots stay at least the specified
        distance away from the ball."""
        ball_pos = self.gs.get_ball_position()
        team = self._team
        if robot_ids is None:
            robot_ids = self.gs.get_robot_ids(team)
        for robot_id in robot_ids:
            self.set_speed_limit(robot_id, speed_limit)
            a = self.gs.get_robot_position(team, robot_id)[:2] - ball_pos
            if np.linalg.norm(a) < distance:
                self.path_find(robot_id, self.find_legal_pos(robot_id))

    def move_randomly(self):
        for robot_id in self.gs.get_robot_ids(self._team):
            self.random_robot(robot_id)

    def timeout(self) -> None:
        """Run a timeout play. All robots should stop whatever they're doing and
        immediate go out of bounds at coordinates:
            TODO: Add coordinates for timeout
        """

    def form_wall(self, ids, distance_from_ball: float = 500) -> None:
        """Form a defensive wall. The robots in ids will form a wall between
        the ball position and the goal at the specified distance, in a
        direction perpendicular to the line between the ball and the center of
        goal and centered on that line.
        """
        ball_pos = self.gs.get_ball_position()
        goal_top, goal_bottom = self.gs.get_defense_goal(self._team)
        goal_center = (goal_top + goal_bottom) / 2
        distance_from_goal = np.linalg.norm(ball_pos - goal_center)
        # TODO: Choose legal position
        block_pos = self.block_goal_center_pos(
            distance_from_goal - distance_from_ball)
        # TODO: Leave right amount of buffer space in offset_vector
        offset_vector = self.perpendicular(ball_pos - goal_center) \
            * self.gs.ROBOT_RADIUS * 2
        wall_positions = []
        for i in range(len(ids)):
            robot_offset = ((i - (len(ids) - 1)/2) * offset_vector)
            robot_offset = np.append(robot_offset, 0)
            wall_positions.append(robot_offset + block_pos)
        self.logger.debug(wall_positions)

        # Assign robot pos based on wall orientation to minimize path crossing
        wall_positions = sorted(
            wall_positions, key=lambda x: np.dot(x[:2], offset_vector))

        ids = sorted(ids, key=lambda x: np.dot(
            self.gs.get_robot_position(self._team, x)[:2],
            offset_vector
        ))
        for i in range(len(ids)):
            # TODO: Use path finding
            self.move_straight(ids[i], wall_positions[i])

    def prepare_penalty(self):
        '''
        Instructions to prepare for when our team takes a penalty
        '''
        penalty_taker_id = None
        ranked_dists = self.rank_intercept_distances()
        if len(ranked_dists):
            penalty_taker_id = ranked_dists[0][0]
        else:
            self.logger.debug("No robot on the field to take penalty!?")
            return
        self.penalty_taker(penalty_taker_id)
