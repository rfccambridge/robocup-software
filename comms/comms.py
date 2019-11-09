import threading
import time
try:
    from radio import Radio
    from robot_commands import RobotCommands
except (SystemError, ImportError):
    from .radio import Radio
    from .robot_commands import RobotCommands


class Comms(object):
    """Comms class spins a thread to repeated send the commands stored in
       gamestate to the robots via radio"""
    def __init__(self, gamestate, team):
        self._gamestate = gamestate
        assert(team in ['blue', 'yellow'])
        self._team = team

        self._radio = None

        self._is_sending = False
        self._sending_thread = None
        self._last_send_loop_time = None

        self._is_receiving = False
        self._receiving_thread = None
        # self._messages_received = []
        self._last_receive_loop_time = None

    def die(self):
        if self._radio is not None:
            self._radio.close()

    def start_sending(self):
        if self._radio is None:
            self._radio = Radio()
        self._is_sending = True
        self._sending_thread = threading.Thread(target=self.sending_loop)
        # set to daemon mode so it will be easily killed
        self._sending_thread.daemon = True
        self._sending_thread.start()

    def start_receiving(self):
        if self._radio is None:
            self._radio = Radio()
        self._is_receiving = True
        self._receiving_thread = threading.Thread(target=self.receiving_loop)
        # set to daemon mode so it will be easily killed
        self._receiving_thread.daemon = True
        self._receiving_thread.start()

    def sending_loop(self):
        while self._is_sending:
            # TODO: move to analysis thread to avoid copying in simulator?
            team_commands = self._gamestate.get_team_commands(self._team)
            for robot_id, robot_commands in team_commands:
                pos = self._gamestate.get_robot_position(self._team, robot_id)
                # stop the robot if we've lost track of it
                if self._gamestate.is_robot_lost(self._team, robot_id):
                    robot_commands.set_speeds(0, 0, 0)
                else:
                    # recalculate the speed the robot should be commanded at
                    robot_commands.derive_speeds(pos)
            # send serialized message for whole team
            team_commands = self._gamestate.get_team_commands(self._team)
            # for robot_id, commands in team_commands.items():
            #     print(commands)
            message = RobotCommands.get_serialized_team_command(team_commands)
            self._radio.send(message)
            if self._last_send_loop_time is not None:
                delta = time.time() - self._last_send_loop_time
                if delta > .3:
                    print("Comms sending loop large delay: " + str(delta))
            self._last_send_loop_time = time.time()
            # yield to other threads - loop only as fast as radio can send
            time.sleep(Radio.MESSAGE_DELAY)

    def receiving_loop(self):
        while self._is_receiving:
            # TODO: save messages for log
            print(self._radio.read())
            # TODO: update relevant data into gamestate
            if self._last_receive_loop_time is not None:
                delta = time.time() - self._last_receive_loop_time
                if delta > .3:
                    print("Comms receiving loop large delay: " + str(delta))
            self._last_receive_loop_time = time.time()
            # yield to other threads - loop at most 20 times per second
            time.sleep(.05)

    def stop_sending_and_receiving(self):
        if self._is_sending:
            self._is_sending = False
            self._sending_thread.join()
            self._sending_thread = None
        if self._is_receiving:
            self._is_receiving = False
            self._receiving_thread.join()
            self._receiving_thread = None
        self.die()

