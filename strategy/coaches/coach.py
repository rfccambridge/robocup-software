"""Role analysis class for strategy."""
import sys
# sys.path.append("../..")
from refbox.referee_pb2 import SSL_Referee

class Coach(object):
    """Coach class that takes in the Strategy class and assembles together high
    level commands."""
    def __init__(self, strategy) -> None:
        """Coach class initialization with a strategy that the coach should
        oversee. 
        
        Args:
            strategy (strategy.Strategy): Strategy object that the Coach should
            run
        """
        self._strategy = strategy
        self.logger = strategy.logger
        self._gs = strategy._gs
        self._command_dict = {
            SSL_Referee.HALT: self.halt,
            SSL_Referee.STOP: self.stop,
            SSL_Referee.FORCE_START: self.force_start,
            SSL_Referee.PREPARE_KICKOFF_YELLOW: self.kickoff if self.is_yellow() else self.defend_kickoff,
            SSL_Referee.PREPARE_KICKOFF_BLUE: self.kickoff if self.is_blue() else self.defend_kickoff,
            SSL_Referee.PREPARE_PENALTY_YELLOW: self.penalty if self.is_yellow() else self.defend_penalty,
            SSL_Referee.PREPARE_PENALTY_BLUE: self.penalty if self.is_blue() else self.defend_penalty,
            SSL_Referee.DIRECT_FREE_YELLOW: self.direct_free if self.is_yellow() else self.defend_direct_free,
            SSL_Referee.DIRECT_FREE_BLUE: self.direct_free if self.is_blue() else self.defend_direct_free,
            SSL_Referee.INDIRECT_FREE_YELLOW: self.indirect_free if self.is_yellow() else self.defend_indirect_free,
            SSL_Referee.INDIRECT_FREE_BLUE: self.indirect_free if self.is_blue() else self.defend_indirect_free,
            SSL_Referee.TIMEOUT_YELLOW: self.timeout,
            SSL_Referee.TIMEOUT_BLUE: self.timeout,
            SSL_Referee.GOAL_YELLOW: self.goal if self.is_yellow() else self.defend_goal,
            SSL_Referee.GOAL_BLUE: self.goal if self.is_blue() else self.defend_goal,
            SSL_Referee.BALL_PLACEMENT_YELLOW: self.ball_placement if self.is_yellow() else self.defend_ball_placement,
            SSL_Referee.BALL_PLACEMENT_BLUE: self.ball_placement if self.is_blue() else self.defend_ball_placement,
        }

    def is_blue(self) -> bool:
        return self._strategy._team == 'blue'

    def is_yellow(self) -> bool:
        return self._strategy._team == 'yellow'
		
    def play(self):
        if self._gs.latest_refbox_message is None:
            return
        self._command_dict[self._gs.latest_refbox_message.command]

    def halt(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def force_start(self):
        raise NotImplementedError

    def kickoff(self):
        self._strategy.kickoff()

    def defend_kickoff(self):
        raise NotImplementedError

    def penalty(self):
        raise NotImplementedError

    def defend_penalty(self):
        raise NotImplementedError

    def direct_free(self):
        raise NotImplementedError

    def defend_direct_free(self):
        raise NotImplementedError

    def indirect_free(self):
        raise NotImplementedError

    def defend_indirect_free(self):
        raise NotImplementedError

    def timeout(self):
        raise NotImplementedError

    def goal(self):
        self.logger.warning('GOOOOOOOOOOOOOOOOOAAAAAAAAAAALLLLLLLLLLLLLLL')
    
    def defend_goal(self):
        self.logger.warning('RIP')

    def ball_placement(self):
        raise NotImplementedError

    def defend_ball_placement(self):
        raise NotImplementedError


            
    

    
