import threading
import time
import math


class Simulator(object):
    """Simulator class spins a thread to update gamestate instead of vision and comms.
       Applies rudimentary physics (movement trajectories) and commands, to allow for
       offline prototyping.
    """
    # TODO: when we get multiple comms, connect to all robots that are available
    def __init__(self, gamestate):
        self._gamestate = gamestate
        self._is_simulating = False
        self._thread = None
        self._last_step_time = None

    def start_simulating(self):
        self._is_simulating = True
        self._thread = threading.Thread(target=self.simulation_loop)
        # set to daemon mode so it will be easily killed
        self._thread.daemon = True
        self._thread.start()
        
    def simulation_loop(self):
        while self._is_simulating:
            # TODO: insert new ball positions according to prediction
            # TODO: insert new robot positions according to commands
            if self._last_step_time is not None:
                delta = time.time() - self._last_step_time
                if delta > .3:
                    print("Simulation loop unexpectedly large delay: " + str(delta))
            self._last_step_time = time.time()
            # yield to other threads - run this loop at most 20 times per second
            time.sleep(.05)

    def stop_simulating(self):
        self._is_simulating = False
        self._thread.join()
        self._thread = None
