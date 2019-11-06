import threading
import time
from .omni import OmniComms

class Comms(object):
    """Comms class spins a thread to repeated send the commands stored in
       gamestate to the robots via radio"""
    # TODO: when we get multiple comms, connect to all robots that are available
    def __init__(self, gamestate, team):
        self._gamestate = gamestate
        assert(team in ['blue', 'yellow'])
        self._team = team

        self._comms = None

        self._is_sending = False
        self._sending_thread = None
        self._last_send_loop_time = None

        self._is_receiving = False
        self._receiving_thread = None
        self._messages_received = []
        self._last_receive_loop_time = None


    def die(self):
        if self._comms is not None:
            self._comms.close()

    def start_sending(self):
        if self._comms is None:
            self._comms = OmniComms()
        self._is_sending = True
        self._sending_thread = threading.Thread(target=self.sending_loop)
        # set to daemon mode so it will be easily killed
        self._sending_thread.daemon = True
        self._sending_thread.start()

    def start_receiving(self):
        if self._comms is None:
            self._comms = OmniComms()
        self._is_receiving = True
        self._receiving_thread = threading.Thread(target=self.receiving_loop)
        # set to daemon mode so it will be easily killed
        self._receiving_thread.daemon = True
        self._receiving_thread.start()        
        
    def sending_loop(self):
        while self._is_sending:
            # compile a single serialized command message for all robots
            multi_command_string = b""
            assert len(self._gamestate.get_robot_ids(self._team)) <= 6, 'too many robots'
            for robot_id in self._gamestate.get_robot_ids(self._team):
                # TODO: move to gamestate so no need to have same logic in simulator?
                robot_commands = self._gamestate.get_robot_commands(self._team, robot_id)
                pos = self._gamestate.get_robot_position(self._team, robot_id)                
                # stop the robot if we've lost track of it
                if self._gamestate.is_robot_lost(self._team, robot_id):
                    robot_commands.set_zero_speeds()
                else:
                    # recalculate the speed the robot should be commanded at
                    robot_commands.derive_speeds(pos)
                command_string = robot_commands.get_serialized_command(robot_id)
                print(robot_commands.deserialize_command(command_string))
                multi_command_string += command_string
            self._comms.send(command_string)

            if self._last_send_loop_time is not None:
                delta = time.time() - self._last_send_loop_time
                if delta > .3:
                    print("Comms sending loop unexpectedly large delay: " + str(delta))
            self._last_send_loop_time = time.time()
            # yield to other threads - run this loop at most 20 times per second
            # Warning - looping too fast might overload throttle, so some commands never sent
            time.sleep(.05)

    def receiving_loop(self):
        while self._is_receiving:
            # TODO: save messages for log
            print(self._comms.read())
            # TODO: update relevant data into gamestate
            if self._last_receive_loop_time is not None:
                delta = time.time() - self._last_receive_loop_time
                if delta > .3:
                    print("Comms receiving loop unexpectedly large delay: " + str(delta))
            self._last_receive_loop_time = time.time()
            # yield to other threads - run this loop at most 20 times per second
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

