"""Role analysis class for strategy."""
# pylint: disable=import-error
from refbox import SSL_Referee


class Coach(object):
    """Coach class that takes in the Strategy class and assembles together high
    level commands.
    See https://robocup-ssl.github.io/ssl-rules/sslrules.html#_referee_commands
    """

    def __init__(self, strategy) -> None:
        """Coach class initialization with a strategy that the coach should
        oversee.

        Args:
            strategy (strategy.Strategy): Strategy object that the Coach should
            run,
        """
        self._strategy = strategy
        self._team = self._strategy._team
        self.logger = strategy.logger
        self.gs = strategy.gs
        self._command_dict = {
            SSL_Referee.HALT: self.halt,
            SSL_Referee.STOP: self.stop,
            SSL_Referee.NORMAL_START: self.normal_start,
            SSL_Referee.FORCE_START: self.force_start,
            SSL_Referee.PREPARE_KICKOFF_YELLOW:
                self.kickoff if self.is_yellow() else self.defend_kickoff,
            SSL_Referee.PREPARE_KICKOFF_BLUE:
                self.kickoff if self.is_blue() else self.defend_kickoff,
            SSL_Referee.PREPARE_PENALTY_YELLOW:
                self.penalty if self.is_yellow() else self.defend_penalty,
            SSL_Referee.PREPARE_PENALTY_BLUE:
                self.penalty if self.is_blue() else self.defend_penalty,
            SSL_Referee.DIRECT_FREE_YELLOW:
                self.direct_free if self.is_yellow() else
                self.defend_direct_free,
            SSL_Referee.DIRECT_FREE_BLUE:
                self.direct_free if self.is_blue() else
                self.defend_direct_free,
            SSL_Referee.INDIRECT_FREE_YELLOW:
                self.indirect_free if self.is_yellow() else
                self.defend_indirect_free,
            SSL_Referee.INDIRECT_FREE_BLUE:
                self.indirect_free if self.is_blue() else
                self.defend_indirect_free,
            SSL_Referee.TIMEOUT_YELLOW:
                self.timeout,
            SSL_Referee.TIMEOUT_BLUE:
                self.timeout,
            SSL_Referee.GOAL_YELLOW:
                self.goal if self.is_yellow() else self.defend_goal,
            SSL_Referee.GOAL_BLUE:
                self.goal if self.is_blue() else self.defend_goal,
            SSL_Referee.BALL_PLACEMENT_YELLOW:
                self.ball_placement if self.is_yellow() else
                self.defend_ball_placement,
            SSL_Referee.BALL_PLACEMENT_BLUE:
                self.ball_placement if self.is_blue() else
                self.defend_ball_placement,
        }

    def is_blue(self) -> bool:
        return self._team == 'blue'

    def is_yellow(self) -> bool:
        return self._team == 'yellow'

    def play(self):
        self.logger.debug("Play was called")
        latest_refbox_message = self.gs.get_latest_refbox_message()
        if latest_refbox_message:
            self._command_dict[latest_refbox_message.command]()
        for robot_id in self.gs.get_robot_ids(self._team):
            current_pos = self.gs.get_robot_position(self._team, robot_id)
            # Get out of illegal positions immediately
            if not self.gs.is_pos_legal(current_pos, self._team, robot_id):
                self.logger.debug(f"Illegal position for robot {robot_id}")
                new_pos = self._strategy.find_legal_pos(robot_id, current_pos)
                self._strategy.path_find(robot_id, new_pos, allow_illegal=True)

    # Functions for dealing with ref commands
    def halt(self):
        self.logger.info("HALT CALLED")
        self._strategy.halt()

    def stop(self):
        self.logger.info("STOP CALLED")
        self._strategy.avoid_ball()

    def normal_start(self):
        self.logger.info("NORMAL START CALLED")
        if self.gs.is_ball_in_play():
            self.open_play()

    def force_start(self):
        self.logger.info("FORCE START CALLED")
        self.open_play()

    def kickoff(self):
        self.logger.info("KICKOFF CALLED")
        self._strategy.kickoff()

    def defend_kickoff(self):
        self.logger.info("DEFEND KICKOFF CALLED")
        self._strategy.kickoff(defending=True)

    def penalty(self):
        self.logger.info("PK CALLED")
        self._strategy.prepare_penalty()

    def defend_penalty(self):
        self.logger.info("DEFEND PK CALLED")

    def direct_free(self):
        self.logger.info("FREE KICK CALLED")

    def defend_direct_free(self):
        self.logger.info("DEFEND FREE KICK CALLED")
        self._strategy.form_wall([1, 2, 3])

    def indirect_free(self):
        raise NotImplementedError

    def defend_indirect_free(self):
        raise NotImplementedError

    def timeout(self):
        self.logger.info("TIMEOUT CALLED")

    def goal(self):
        self.logger.warning('GOOOOOOOOOOOOOOOOOAAAAAAAAAAALLLLLLLLLLLLLLL')

    def defend_goal(self):
        self.logger.warning('RIP')

    def ball_placement(self):
        raise NotImplementedError

    def defend_ball_placement(self):
        raise NotImplementedError

    # Functions for dealing with subsets of game situations
    def open_play(self):
        '''
        Deals with cases where the game is running and we are not in a
        special situation such as a free kick, penalty kick, etc.
        '''
        raise NotImplementedError
