import numpy as np


# pylint: disable=import-error
from coordinator import Provider

# import lower-level strategy logic that we've separated for readability
try:
    from utils import Utils
    from analysis import Analysis
    from actions import Actions
    from routines import Routines
    from roles import Roles
    from plays import Plays
    from coaches import *  # noqa
except (SystemError, ImportError, ModuleNotFoundError):
    from .utils import Utils
    from .actions import Actions
    from .routines import Routines
    from .roles import Roles
    from .analysis import Analysis
    from .coaches import *  # noqa
    from .plays import Plays


class Strategy(Provider, Utils, Analysis, Actions, Routines, Roles, Plays):
    """Control loop for playing the game. Calculate desired robot actions,
       and enters commands into gamestate to be sent by comms"""
    def __init__(self, team, strategy_name):
        super().__init__()
        assert(team in ['blue', 'yellow'])
        self._team = team
        self._strategy_name = strategy_name
        self._owned_fields = ['_blue_robot_commands'] if team == 'blue' \
            else ['_yellow_robot_commands']

        # state for reducing frequency of expensive calls
        # (this also helps reduce oscillation)
        self._last_pathfind_times = {}  # robot_id : timestamp

    def pre_run(self):
        # print info + initial state for the mode that is running
        self.logger.info("\nRunning strategy for {} team, mode: {}".format(
            self._team, self._strategy_name
        ))
        if self._strategy_name == "UI":
            self.logger.info("""
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
            self.logger.info("NOT RUNNING SYSTEMANICALLY")
        if self._strategy_name == "entry_video":
            self.logger.info("2020 Registration Video Procedure!")
            self.video_phase = 1
        if self._strategy_name == "goalie_test":
            self._goalie_id = None
        if self._strategy_name == "attacker_test":
            self._attacker_id = None
        if self._strategy_name == "defender_test":
            self._defender_id = None
        if self._strategy_name == "full_team_test":
            pass
        if self._strategy_name == "full_game":
            self.logger.info("default strategy for playing a full game")

    def run(self):
        ref = self.gs.get_latest_refbox_message()
        if ref is not None:
            self.logger.debug(f"Stage: {ref.stage} Command: {ref.command}")
        # run the strategy corresponding to the given mode
        if self._strategy_name == "UI":
            self.UI()
        elif self._strategy_name == "goalie_test":
            self.goalie_test()
        elif self._strategy_name == "attacker_test":
            self.attacker_test()
        elif self._strategy_name == "defender_test":
            self.defender_test()
        elif self._strategy_name == "full_team_test":
            self.full_team_test()
        elif self._strategy_name == "entry_video":
            self.entry_video()
        elif self._strategy_name == "random_robot":
            self.random_robot_test()
        elif self._strategy_name == "full_game":
            self.full_game()
        else:
            # self.logger.exception('(unrecognized mode, doing nothing)')
            pass
        # Reset kicking commands after kick takes place and charge is zero
        # team_commands = self.gs.get_team_commands(self._team)
        for robot_id, commands in self.gs.get_team_commands(self._team).items():  # noqa
            robot_status = self.gs.get_robot_status(self._team, robot_id)
            if robot_status.charge_level == 0:
                commands.is_kicking = False

    # follow the user-input commands through visualizer
    def UI(self):
        _ = self.gs.get_ball_last_update_time()

        if self.gs.viz_inputs['user_selected_robot'] is not None:
            team, robot_id = self.gs.viz_inputs['user_selected_robot']
            # self.logger.info(self.gs.ball_in_dribbler(team, robot_id))
            if team == self._team:
                commands = self.gs.get_robot_commands(self._team, robot_id)
                # apply simple commands
                commands.is_charging = self.gs.viz_inputs['user_charge_command']  # noqa
                commands.is_kicking = self.gs.viz_inputs['user_kick_command']  # noqa
                commands.is_dribbling = self.gs.viz_inputs['user_dribble_command']  # noqa
                # set goal pos to click location on visualization window
                if self.gs.viz_inputs['user_click_position'] is not None:
                    x, y = self.gs.viz_inputs['user_click_position']
                    if self.gs.viz_inputs['user_drag_vector'].any():
                        # face the dragged direction
                        dx, dy = self.gs.viz_inputs['user_drag_vector']
                        w = np.arctan2(dy, dx)
                    else:
                        w = None
                    goal_pos = np.array([x, y, w])
                    # Use pathfinding
                    # self.move_straight(robot_id, goal_pos, is_urgent=True)
                    # self.path_find(robot_id, goal_pos)
                    self.path_find(robot_id, goal_pos)
                    # self.logger.info("UI CLICK!")
                    # self.set_dribbler(robot_id, True)
                    # self.pivot_with_ball(robot_id, goal_pos)

    def goalie_test(self):
        if self.gs.user_selected_robot is not None:
            team, robot_id = self.gs.viz_inputs['user_selected_robot']
            if team == self._team:
                self._goalie_id = robot_id
        if self._goalie_id is not None:
            self.goalie(self._goalie_id)

    def random_robot_test(self):
        for robot_id in self.gs.get_robot_ids(self._team):
            self.random_robot(robot_id)

    def attacker_test(self):
        # team = self._team
        ranked_dists = self.rank_intercept_distances()
        if len(ranked_dists) > 0:
            self.attacker_on_ball(ranked_dists[0][0])
            self.attacker_off_ball(ranked_dists[1][0])
            self.attacker_off_ball2(ranked_dists[2][0])
        # if self.gs.viz_inputs['user_selected_robot'] is not None:
        #     team, robot_id = self.gs.viz_inputs['user_selected_robot']
        #     if team == self._team:
        #         self._attacker_id = robot_id
        # if self._attacker_id is not None:
        #     self.attacker(self._attacker_id)

    def defender_test(self):

        # if self.gs.viz_inputs['user_selected_robot'] is not None:
        #     team, robot_id = self.gs.viz_inputs['user_selected_robot']
        #     if team == self._team:
        #         self._defender_id = robot_id
        # if self._defender_id is not None:
        #     self.defender(self._defender_id)
        ranked_dists = self.rank_intercept_distances()
        if len(ranked_dists) > 0:
            self.defender(ranked_dists[0][0])
            self.defender2(ranked_dists[1][0])
        goalie_id = self.gs.get_goalie_id(self._team)
        # TODO: Fix this part
        if goalie_id not in self.gs.get_robot_ids(self._team):
            goalie_id = 1
        self.goalie(goalie_id)
        # for robot_id in self.gs.get_robot_ids(self._team):
        #     self.defender(robot_id)

    def full_team_test(self):
        '''
        Test of a full team setup
        '''
        team = self._team
        unassigned_ids = list(self.gs.get_robot_ids(team))

        # Assign goalie
        if len(unassigned_ids) > 0:
            goalie_id = self.gs.get_goalie_id(self._team)
            # TODO: Fix this part
            if goalie_id not in self.gs.get_robot_ids(self._team):
                goalie_id = 1
            unassigned_ids.remove(goalie_id)
            self.goalie(goalie_id)

        # Figure out whether we are on attack or defense
        offense_team, robot_id = self.which_robot_has_ball()
        ranked_dists = self.rank_intercept_distances(ids=unassigned_ids)
        if offense_team is not None and offense_team == team:
            # Play offense
            # Assign the robot closest to the ball to get the ball
            if len(ranked_dists) > 0:
                attacker_on_ball_id = ranked_dists[0][0]
                unassigned_ids.remove(attacker_on_ball_id)
                self.attacker_on_ball(attacker_on_ball_id)

            # Find the furthest back unassigned robot and have it play defense
            team_posns = {}
            for id in unassigned_ids:
                team_posns[id] = self.gs.get_robot_position(team, id)
            best_defenders = sorted(
                team_posns.items(),
                key=lambda x: x[1][0],
                reverse=(not self.defending_on_left())
            )
            if len(best_defenders) > 0:
                defender2_id = best_defenders[0][0]
                unassigned_ids.remove(defender2_id)
                self.defender2(defender2_id)

            # Assign two robots to go forward
            team_posns = {}
            for id in unassigned_ids:
                team_posns[id] = self.gs.get_robot_position(team, id)
            best_attackers = sorted(
                team_posns.items(),
                key=lambda x: self.rate_attacker_pos(x[1], x[0]),
                reverse=True
            )
            if len(best_attackers) > 0:
                attacker_off_ball_id = best_attackers[0][0]
                unassigned_ids.remove(attacker_off_ball_id)
                self.attacker_off_ball(attacker_off_ball_id)
            if len(best_attackers) > 1:
                attacker_off_ball2_id = best_attackers[1][0]
                unassigned_ids.remove(attacker_off_ball2_id)
                self.attacker_off_ball2(attacker_off_ball2_id)

            # Assign one robot to stay back as a safe passing option
            if len(best_attackers) > 2:
                deep_attacker_id = best_attackers[2][0]
                unassigned_ids.remove(deep_attacker_id)
                self.deep_attacker(deep_attacker_id)
        else:
            # Play defense
            ranked_dists = self.rank_intercept_distances(ids=unassigned_ids)
            # Assign nearest-to-ball robot to press the other team
            if len(ranked_dists) > 0:
                defender_id = ranked_dists[0][0]
                unassigned_ids.remove(defender_id)
                self.defender(defender_id)

            # Find two furthest back unassigned robots and have them stay back
            team_posns = {}
            for id in unassigned_ids:
                team_posns[id] = self.gs.get_robot_position(team, id)
            best_defenders = sorted(
                team_posns.items(),
                key=lambda x: x[1][0],
                reverse=(not self.defending_on_left())
            )
            if len(best_defenders) > 0:
                defender2_id = best_defenders[0][0]
                unassigned_ids.remove(defender2_id)
                self.defender2(defender2_id)
            if len(best_defenders) > 1:
                defender3_id = best_defenders[1][0]
                unassigned_ids.remove(defender3_id)
                self.defender2(defender3_id)

            # Have up to two robots stay in attacking positions
            team_posns = {}
            for id in unassigned_ids:
                team_posns[id] = self.gs.get_robot_position(team, id)
            best_attackers = sorted(
                team_posns.items(),
                key=lambda x: self.rate_attacker_pos(x[1], x[0]),
                reverse=True
            )
            # One goes forward
            if len(best_attackers) > 0:
                attacker_off_ball_id = best_attackers[0][0]
                unassigned_ids.remove(attacker_off_ball_id)
                self.attacker_off_ball(attacker_off_ball_id)
            # One gets into a safe passing position in case a teammate
            # suddenly gets the ball and needs to pass
            if len(best_attackers) > 1:
                deep_attacker_id = best_attackers[1][0]
                unassigned_ids.remove(deep_attacker_id)
                self.deep_attacker(deep_attacker_id)
        return

    def entry_video(self):
        robot_id_0 = 4
        robot_id_1 = 11
        # where the initial pass will be received
        reception_pos = np.array([3200., 0., self.robot_face_ball(robot_id_1)])
        pass_velocity = 800
        shoot_velocity = 1200
        # reduce for real life b.c. miniature field
        # pass_velocity = 400
        # shoot_velocity = 500

        if self.video_phase >= 6:
            self.goalie(robot_id_1, is_opposite_goal=True)

        if self.video_phase == 1:
            # robot 0 gets the ball
            got_ball = self.get_ball(robot_id_0, charge_during=pass_velocity)
            # robot 1 moves to pos to receive a pass
            self.path_find(robot_id_1, reception_pos)
            # transition once robot 0 has ball (robot 1 can keep moving)
            if got_ball:
                self.video_phase += 1
                self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 2:
            self.path_find(robot_id_1, reception_pos)
            # robot 0 makes the pass towards reception pos
            kicked = self.prepare_and_kick(robot_id_0,
                                           reception_pos,
                                           pass_velocity)
            if kicked:
                self.video_phase += 1
                self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 3:
            # robot 1 receives ball
            got_ball = self.get_ball(robot_id_1, charge_during=shoot_velocity)
            if got_ball:
                self.video_phase += 1
                self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 4:
            # robot 1 moves to best kick pos to shoot
            goal = self.gs.get_attack_goal(self._team)
            center_of_goal = (goal[0] + goal[1]) / 2
            shot = self.prepare_and_kick(robot_id_1,
                                         center_of_goal,
                                         shoot_velocity)
            if shot:
                self.video_phase += 1
                self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 5:
            self.set_dribbler(robot_id_1, False)
            self.kick_ball(robot_id_1)
            self.video_phase += 1
            self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 6:
            self.video_phase += 1
            self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 7:
            if self.gs.get_ball_position()[0] > 3000:
                return
            # Wait for person to place a ball, then have robot 1 go to it
            got_ball = self.get_ball(robot_id_0, charge_during=shoot_velocity)
            if got_ball:
                self.video_phase += 1
                self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 8:
            # Robot 1 moves to best kick pos to shoot
            goal = self.gs.get_attack_goal(self._team)
            center_of_goal = (goal[0] + goal[1]) / 2
            shot = self.prepare_and_kick(robot_id_0,
                                         center_of_goal,
                                         shoot_velocity)
            if shot:
                self.video_phase += 1
                self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 9:
            self.set_dribbler(robot_id_0, False)
            self.kick_ball(robot_id_0)
            # Loop back to placing the ball
            self.video_phase += 1
            self.logger.info("Moving to video phase %s", self.video_phase)
        elif self.video_phase == 10:
            if self.gs.get_ball_position()[0] > 3000:
                self.video_phase = 7
                self.logger.info("Moving back to video phase %s",
                                 self.video_phase)
        else:
            pass

    def full_game(self):
        # pylint: disable=undefined-variable
        coach = Coach(self)  # noqa
        coach.play()
