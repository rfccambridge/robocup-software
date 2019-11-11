import threading
import time
import numpy as np
from collections import deque


class Simulator(object):
    """Simulator class spins to update gamestate instead of vision and comms.
       Applies rudimentary physics and commands, to allow offline prototyping.
    """
    # TODO: when we get multiple comms, connect to all available robots
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

    # adjust timestamps so it's like we've just seen the data
    # assumes deque elements are in the form (timestamp, data)
    def adjust_timestamps(self, deque_data):
        time_offset = time.time() - deque_data[0][0]
        adjusted_data = deque([])
        for timestamp, data in deque_data:
            adjusted_data.append((timestamp + time_offset, data))
        return adjusted_data

    def initialize_ball_move(self):
        # bypass gamestate "private" variable >:O
        # Some real-life collected ball data when it was moving
        ball_data = deque([
            (1572297310.7425327, np.array([1241.970703125, 260.635528564453])),
            (1572297310.7324636, np.array([1218.429443359, 252.887451171875])),
            (1572297310.7223923, np.array([1218.429443359, 252.887451171875])),
            (1572297310.7123000, np.array([1182.462158203, 244.924942016601])),
            (1572297310.7022493, np.array([1182.462158203, 244.924942016601])),
            (1572297310.6921763, np.array([1125.279785150, 245.633651733398])),
        ], maxlen=20)
        self._gamestate._ball_position = self.adjust_timestamps(ball_data)

    def start_simulating(self):
        self._is_simulating = True
        self._thread = threading.Thread(target=self.simulation_loop)
        # set to daemon mode so it will be easily killed
        self._thread.daemon = True
        self._thread.start()

    def simulation_loop(self):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()

        # initialize a scenario
        self.put_fake_ball(np.array([0, 0]))
        self.put_fake_robot('blue', 8, np.array([100, 100, 0]))
        self.initialize_ball_move()

        while self._is_simulating:
            delta_time = 0
            if self._last_step_time is not None:
                delta_time = time.time() - self._last_step_time
                if delta_time > .3:
                    print("Simulation loop large delay: " + str(delta_time))
            self._last_step_time = time.time()

            # move ball according to prediction
            ball_pos = self._gamestate.get_ball_position()
            if ball_pos is not None:
                new_ball_pos = self._gamestate.predict_ball_pos(delta_time)
                # print("dt: {}, new_pos: {}".format(delta_time, new_ball_pos))
                # print(time.time())
                # print("v: {}".format(self._gamestate.get_ball_velocity()))
                # print(self._gamestate.predict_ball_pos(0))
                # print(self._gamestate.predict_ball_pos(1))

                # print(self._gamestate.get_ball_velocity())
                self._gamestate.update_ball_position(new_ball_pos)
                # TODO: collisions, + randomness?

            for team in ['blue', 'yellow']:
                # move robots according to commands
                team_commands = self._gamestate.get_team_commands(team)
                for robot_id, robot_commands in team_commands.items():
                    pos = self._gamestate.get_robot_position(team, robot_id)
                    new_pos = robot_commands.predict_pos(pos, delta_time)
                    self._gamestate.update_robot_position(
                        team, robot_id, new_pos
                    )
                # refresh positions of all robots
                for robot_id in self._gamestate.get_robot_ids(team):
                    pos = self._gamestate.get_robot_position(team, robot_id)
                    self._gamestate.update_robot_position(team, robot_id, pos)
            # yield to other threads - loop at most 20 times per second
            time.sleep(.05)

    def stop_simulating(self):
        if self._is_simulating:
            self._is_simulating = False
            self._thread.join()
            self._thread = None
