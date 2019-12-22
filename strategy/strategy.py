import threading
import numpy as np
import time

# import lower-level strategy logic
try:
    from actions import Actions
    from routines import Routines
    from roles import Roles
except (SystemError, ImportError):
    from .actions import Actions
    from .routines import Routines
    from .roles import Roles


class Strategy(Actions, Routines, Roles):
    """Control loop for playing the game. Uses gamestate to calculate desired
       robot actions, and enters commands into gamestate to be sent by comms"""
    def __init__(self, gamestate, team):
        assert(team in ['blue', 'yellow'])
        self._team = team
        self._gamestate = gamestate

        # for reducing frequency of expensive calls
        # (this also helps reduce oscillation)
        self._last_RRT_times = {}  # robot_id : timestamp

        self._is_controlling = False
        self._control_thread = None
        self._control_loop_sleep = None
        self._last_control_loop_time = None
        self._mode = None

    def start_controlling(self, mode, loop_sleep):
        self._mode = mode
        self._control_loop_sleep = loop_sleep
        self._is_controlling = True
        self._control_thread = threading.Thread(target=self.control_loop)
        # set to daemon mode so it will be easily killed
        self._control_thread.daemon = True
        self._control_thread.start()
        print("\nRunning strategy for {} team, mode: {}".format(
            self._team, self._mode)
        )
        if self._mode == "UI":
            print("""
            Using UI Controls!
            Robots:
            - Click to select
            - Click to set goal position (drag for direction)
            - 'd' to toggle dribbler
            - 'c' to charge kicker, 'k' to kick
            Ball (IF SIMULATING):
            - Click or 'b' to select
            - Click to place (drag for speed)
            """)

        if self._mode == "entry_video":
            print("2020 Registration Video Procedure!")
            self.video_phase = 1

    def stop_controlling(self):
        if self._is_controlling:
            self._is_controlling = False
            self._control_thread.join()
            self._control_thread = None

    def control_loop(self):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()
        while self._is_controlling:
            # run the strategy corresponding to the given mode
            if self._mode == "UI":
                self.UI()
            elif self._mode == "entry_video":
                self.entry_video()
            else:
                print('(unrecognized mode, doing nothing)')

            # tell all robots to refresh their speeds based on waypoints
            team_commands = self._gamestate.get_team_commands(self._team)
            team_commands = list(team_commands.items())
            for robot_id, robot_commands in team_commands:
                # stop the robot if we've lost track of it
                if self._gamestate.is_robot_lost(self._team, robot_id):
                    robot_commands.set_speeds(0, 0, 0)
                else:
                    # recalculate the speed the robot should be commanded at
                    pos = self._gamestate.get_robot_position(self._team, robot_id)
                    robot_commands.derive_speeds(pos)

            if self._last_control_loop_time is not None:
                delta = time.time() - self._last_control_loop_time
                if delta > self._control_loop_sleep * 3:
                    print("Control loop large delay: " + str(delta))
            self._last_control_loop_time = time.time()
            # yield to other threads
            time.sleep(self._control_loop_sleep)

    # follow the user-input commands through visualizer
    def UI(self):
        gs = self._gamestate
        if gs.user_selected_robot is not None:
            team, robot_id = gs.user_selected_robot
            if team == self._team:
                commands = gs.get_robot_commands(self._team, robot_id)
                # apply simple commands
                commands.is_charging = gs.user_charge_command
                commands.is_kicking = gs.user_kick_command
                commands.is_dribbling = gs.user_dribble_command
                # set goal pos to click location on visualization window
                if gs.user_click_position is not None:
                    x, y = gs.user_click_position
                    if gs.user_drag_vector.any():
                        # face the dragged direction
                        dx, dy = gs.user_drag_vector
                        w = np.arctan2(dy, dx)
                    else:
                        w = None
                    goal_pos = np.array([x, y, w])
                    # Use pathfinding
                    self.path_find(robot_id, goal_pos)

    def entry_video(self):
        reception_pos = np.array([3200, 0, 0])
        pass_velocity = 1000
        shoot_velocity = 2000
        if self.video_phase == 1:
            # robot 0 moves to midpoint of interception range to recieve ball
            intercept_range = self.intercept_range(0)
            if intercept_range is None:
                print("intercept Range is none")
                return
            intercept_point = (intercept_range[0]+intercept_range[1])/2
            intercept_angle = self.robot_face_ball(0)
            intercept_point = self._gamestate.dribbler_to_robot_pos(
                intercept_point,
                intercept_angle
            )
            self.set_dribbler(0, True)
            self.path_find(0, intercept_point)
            # robot 1 moves to pos to receive a pass
            reception_pos[2] = self.robot_face_ball(1)
            self.path_find(1, reception_pos)
            # start charging up
            self.charge_up_to(0, pass_velocity)
            if self._gamestate.ball_in_dribbler(self._team, 0):
                self.video_phase += 1
                print("!!! Moving to video phase {}".format(self.video_phase))
        elif self.video_phase == 2:
            # robot 0 moves to ideal kicking position
            done_pivoting = self.pivot_with_ball(0, reception_pos)
            done_charging = self.charge_up_to(0, pass_velocity)
            if done_pivoting and done_charging and self.is_done_moving(1):
                self.video_phase += 1
                self.kick_ball(0)
                print("Moving to video phase {}".format(self.video_phase))
        elif self.video_phase == 3:
            self.set_dribbler(1, True)
            # robot 2 finds best pos to receive
            intercept_range = self.intercept_range(1)
            intercept_point = intercept_range[0]
            intercept_angle = self.robot_face_ball(1)
            intercept_point = self._gamestate.dribbler_to_robot_pos(
                intercept_point,
                intercept_angle
            )
            self.move_straight(1, intercept_point)
            self.charge_up_to(1, shoot_velocity)
            if self._gamestate.ball_in_dribbler(self._team, 1):
                self.video_phase += 1
                print("Moving to video phase {}".format(self.video_phase))
        elif self.video_phase == 4:
            # robot 1 moves to best kick pos to shoot
            goal = self._gamestate.get_attack_goal(self._team)
            center_of_goal = (goal[0]+goal[1]) / 2
            self.pivot_with_ball(1, center_of_goal)
            if self.charge_up_to(1, shoot_velocity) and \
               self._gamestate.ball_in_dribbler(self._team, 1):
                self.video_phase += 1
                print("Moving to video phase {}".format(self.video_phase))
        elif self.video_phase == 5:
            self.set_dribbler(1, False)
            self.kick_ball(1)
            self.video_phase += 1
        else:
            pass
