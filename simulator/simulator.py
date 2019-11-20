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
        self._simulation_loop_sleep = None
        self._last_step_time = None

        self._initial_setup = None

    # TODO: flush out system for initializing test scenarios
    def put_fake_robot(self, team, robot_id, position):
        self._gamestate.update_robot_position(team, robot_id, position)

    # initialize ball position data to reflect desired position + velocity
    def put_fake_ball(self, position, velocity=np.array([0, 0])):
        # use small dt to minimize deceleration correction
        dt = .05
        prev_pos = position - velocity * dt
        self._gamestate._ball_position.appendleft((time.time() - dt, prev_pos))
        self._gamestate._ball_position.appendleft((time.time(), position))
        # print(f"{self._gamestate._ball_position}")
        # print(f"v: {self._gamestate.get_ball_velocity()}")

    def start_simulating(self, inital_setup, loop_sleep):
        self._initial_setup = inital_setup
        self._simulation_loop_sleep = loop_sleep
        self._is_simulating = True
        self._thread = threading.Thread(target=self.simulation_loop)
        # set to daemon mode so it will be easily killed
        self._thread.daemon = True
        self._thread.start()

    def simulation_loop(self):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()
        print("\nSimulator running with initial setup: {}".format(
            self._initial_setup
        ))
        # initialize the chosen scenario
        if self._initial_setup == 'full_teams':
            for i in range(1, 7):
                left_pos = np.array([-3000, 200 * (i - 3.5), 0])
                right_pos = np.array([3000, 200 * (i - 3.5), 3.14])
                if self._gamestate.is_blue_defense_side_left:
                    blue_pos = left_pos
                    yellow_pos = right_pos
                else:
                    blue_pos = right_pos
                    yellow_pos = left_pos
                self.put_fake_robot('blue', i, blue_pos)
                self.put_fake_robot('yellow', i, yellow_pos)
            self.put_fake_ball(np.array([0, 0]))
        elif self._initial_setup == "moving_ball":
            self.put_fake_robot('blue', 1, np.array([0, 0, 0]))
            self.put_fake_ball(np.array([1000, 1200]), np.array([0, -1200]))
        else:
            print('(initial_setup not recognized, empty field)')

        # run the simulation loop
        while self._is_simulating:
            delta_time = 0
            if self._last_step_time is not None:
                delta_time = time.time() - self._last_step_time
                if delta_time > self._simulation_loop_sleep * 3:
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

                # print(self._gamestate.get_ball_velocity())
                self._gamestate.update_ball_position(new_ball_pos)

            for (team, robot_id), robot_commands in \
                    self._gamestate.get_all_robot_commands():
                # move robots according to commands
                pos = self._gamestate.get_robot_position(team, robot_id)
                new_pos = robot_commands.predict_pos(pos, delta_time)
                self._gamestate.update_robot_position(
                    team, robot_id, new_pos
                )

            for (team, robot_id), pos in \
                    self._gamestate.get_all_robot_positions():
                # refresh positions of all robots
                pos = self._gamestate.get_robot_position(team, robot_id)
                self._gamestate.update_robot_position(team, robot_id, pos)

                # handle collisions with other robots
                for (team2, robot_id2), pos2 in \
                        self._gamestate.get_all_robot_positions():
                    if (team2, robot_id2) != (team, robot_id) and \
                       self._gamestate.robot_overlap(pos, pos2).any():
                        overlap = self._gamestate.robot_overlap(pos, pos2)
                        overlap = np.append(overlap, 0)
                        self._gamestate.update_robot_position(
                            team, robot_id, pos - overlap / 2)
                        self._gamestate.update_robot_position(
                            team2, robot_id2, pos2 + overlap / 2)
                # collision with ball
                ball_overlap = self._gamestate.ball_overlap(pos)
                if ball_overlap.any():
                    ball_pos = self._gamestate.get_ball_position()
                    new_pos = ball_pos + ball_overlap
                    self._gamestate.update_ball_position(new_pos)
            # yield to other threads
            time.sleep(self._simulation_loop_sleep)

    def stop_simulating(self):
        if self._is_simulating:
            self._is_simulating = False
            self._thread.join()
            self._thread = None
