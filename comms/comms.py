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
            self._comms.send(self._gamestate.get_serialized_team_command(self._team))

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

