import threading
import time
import numpy as np


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

    # initialize ball position data to reflect desired position + velocity
    def put_fake_ball(self, position, velocity=np.array([0, 0])):
        # use small dt to minimize deceleration correction
        dt = .05
        self._gamestate.update_ball_position(position - velocity * dt)
        time.sleep(dt)
        self._gamestate.update_ball_position(position)

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
        self.put_fake_ball(np.array([0, -100]), np.array([1000, 0]))
        self.put_fake_robot('blue', 8, np.array([100, 100, 0]))
        self.put_fake_robot('blue', 7, np.array([100, 300, 0]))

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
                    # collisions between robots - TODO: make symmetric!!!
                    for other in self._gamestate.get_all_robot_positions():
                        if (other != pos).any():
                            overlap = self._gamestate.robot_overlap(other, pos)
                            overlap = np.append(overlap, 0)
                            self._gamestate.update_robot_position(
                                team,
                                robot_id,
                                pos + overlap / 2
                            )
                    # collision with ball
                    ball_overlap = self._gamestate.ball_overlap(pos)
                    if ball_overlap.any():
                        ball_pos = self._gamestate.get_ball_position()
                        self._gamestate.update_ball_position(ball_pos + ball_overlap)
            # yield to other threads - loop at most 20 times per second
            time.sleep(.05)

    def stop_simulating(self):
        if self._is_simulating:
            self._is_simulating = False
            self._thread.join()
            self._thread = None
