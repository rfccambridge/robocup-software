import threading
import time
from coordinator import Provider

try:
    from radio import Radio
    from robot_commands import RobotCommands
except (SystemError, ImportError):
    from .radio import Radio
    from .robot_commands import RobotCommands


class Comms(Provider):
    """Comms class spins a thread to repeated send the commands stored in
       gamestate to the robots via radio"""
    def __init__(self, team, is_second_comms=False):
        super().__init__()
        assert(team in ['blue', 'yellow'])
        self._team = team

        self._is_second_comms = is_second_comms
        self._radio = None

        # self._receive_loop_sleep = Radio.MESSAGE_DELAY
        # self._messages_received = []
        # self._last_receive_loop_time = None

    def pre_run(self):
        if self._radio is None:
            self._radio = Radio(self._is_second_comms)

    def run(self):
        team_commands = self.gs.get_team_commands(self._team)
        # send serialized message for whole team
        message = RobotCommands.get_serialized_team_command(team_commands)
        self._radio.send(message)
        for robot_id, commands in team_commands.items():
            # print(commands)
            # simulate charge of capacitors according to commands
            if commands.is_charging:
                commands.simulate_charge(self.delta_time)
            # TODO: UNTESTED
            if commands.is_kicking:
                commands.is_kicking = False
                commands.charge_level = 0
        # sleep to avoid spamming the xbee radio
        time.sleep(Radio.MESSAGE_DELAY)

    def post_run(self):
        if self._radio is not None:
            self._radio.close()

    # def start_receiving(self, loop_sleep):
    #     self._receive_loop_sleep = loop_sleep
    #     if self._radio is None:
    #         self._radio = Radio(self._is_second_comms)
    #     self._is_receiving = True
    #     self._receiving_thread = threading.Thread(target=self.receiving_loop)
    #     # set to daemon mode so it will be easily killed
    #     self._receiving_thread.daemon = True
    #     self._receiving_thread.start()

    # def receiving_loop(self):
    #     self.gs.wait_until_game_begins()
    #     while self._is_receiving:
    #         # TODO: save messages for log
    #         print(self._radio.read())
    #         # TODO: update relevant data into gamestate
    #         if self._last_receive_loop_time is not None:
    #             delta = time.time() - self._last_receive_loop_time
    #             if delta > .3:
    #                 print("Comms receiving loop large delay: " + str(delta))
    #         self._last_receive_loop_time = time.time()
    #         # yield to other threads
    #         time.sleep(self._receive_loop_sleep)
