# import time
# import numpy as np
# from typing import Tuple
import logging
from coordinator import Provider  # pylint: disable=import-error

logger = logging.getLogger(__name__)


class SSLSimulator(Provider):
    ''' Class that handles communication with SSL simulator
    '''

    def SSLSimulator(self):
        super.__init__()
        self.logger = None
        self._owned_fields = [
            # act as vision provider
            '_ball_position',
            '_blue_robot_positions',
            '_yellow_robot_positions',
            # also act as robot feedback
            '_blue_robot_status',
            '_yellow_robot_status',
        ]

    def run(self):
        # Receive new GS
        # Create outgoing message
        self.create_control_message()
        # Receive incoming SSL simulator message
        self.parse_feedback_message()
        # Update GS
        self.update_gs()

    def create_control_message(self):
        # Look at robot commands for our team
        # May have to handle robot charge level separately
        raise NotImplementedError

    def parse_feedback_message(self):
        # Update ball and robot positions (may require separate fnxn)
        # Get info on robot statuses
        raise NotImplementedError

    def update_gs(self):
        raise NotImplementedError

    def get_kick_speed(self):
        # Check charge level and return speed
        raise NotImplementedError
