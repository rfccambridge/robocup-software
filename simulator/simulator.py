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

    # TODO: flush out system for initializing test scenarios
    def put_fake_robot(self, team, robot_id, position):
        self._gamestate.update_robot_position(team, robot_id, position)

    def put_fake_ball(self, position):
        self._gamestate.update_ball_position(position)

    # Some real-life collected ball data to use:
        #deque([(1572297310.7425327, (1241.970703125, 260.6355285644531)), (1572297310.7324636, (1218.429443359375, 252.887451171875)), (1572297310.7223923, (1218.429443359375, 252.887451171875)), (1572297310.7123, (1182.462158203125, 244.92494201660156)), (1572297310.7022493, (1182.462158203125, 244.92494201660156)), (1572297310.6921763, (1125.27978515625, 245.63365173339844)), (1572297310.6820886, (1125.27978515625, 245.63365173339844)), (1572297310.6720102, (1108.6162109375, 254.580322265625)), (1572297310.6619406, (1108.6162109375, 254.580322265625)), (1572297310.6518548, (1071.0198974609375, 252.38209533691406)), (1572297310.6417856, (1071.0198974609375, 252.38209533691406)), (1572297310.631708, (1025.57373046875, 246.82630920410156)), (1572297310.6216369, (1025.57373046875, 246.82630920410156)), (1572297310.6115437, (985.090087890625, 248.5403594970703)), (1572297310.6014657, (985.090087890625, 248.5403594970703)), (1572297310.59138, (944.6881713867188, 246.3601837158203)), (1572297310.581291, (944.6881713867188, 246.3601837158203)), (1572297310.5712094, (896.4560546875, 241.21607971191406)), (1572297310.5611184, (855.451904296875, 246.6865997314453)), (1572297310.5510397, (855.451904296875, 246.6865997314453))], maxlen=20)


    def start_simulating(self):
        self._is_simulating = True
        self._thread = threading.Thread(target=self.simulation_loop)
        # set to daemon mode so it will be easily killed
        self._thread.daemon = True
        self._thread.start()
        
    def simulation_loop(self):
        while self._is_simulating:
            assert(False)
            # TODO: insert new ball positions according to prediction
            ball_pos = self._gamestate.get_ball_position()
            if ball_pos is not None:
                self._gamestate.update_ball_position(ball_pos)
            # TODO: insert new robot positions according to commands
            for team in ['blue', 'yellow']:
                for robot_id in self._gamestate.get_robot_ids(team):
                    pos = self._gamestate.get_robot_position(team, robot_id)
                    self._gamestate.update_robot_position(team, robot_id, pos)
                    
            if self._last_step_time is not None:
                delta = time.time() - self._last_step_time
                if delta > .3:
                    print("Simulation loop unexpectedly large delay: " + str(delta))
            self._last_step_time = time.time()
            # yield to other threads - run this loop at most 20 times per second
            time.sleep(.05)

    def stop_simulating(self):
        if self._is_simulating is not None:
            self._is_simulating = False
            self._thread.join()
            self._thread = None
