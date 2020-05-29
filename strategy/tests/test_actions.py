import numpy as np

from ..actions import Actions
from ..strategy import Strategy

from simulator.simulator import Simulator

team = "blue"
strategy_name = ""

def test_pivot_with_ball():
    """ Tests pivot_with_ball in simple case of empty field and 90 degree turn.
    Passes if the robot begins to turn in the shorter path to the goal direction
    while remaining close to the ball.
    """
    CLOSE_ENOUGH_FACTOR = 1.25
    simulator = Simulator("clear_field_kickoff_test")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    start_pos = gs.get_robot_position(team, 1)
    ball_pos = gs.get_ball_position()
    strategy.pivot_with_ball(1, np.array([0, 1000]))
    goal_pos = strategy.get_goal_pos(1)
    assert(goal_pos[2] > start_pos[2])
    assert(np.linalg.norm(goal_pos[:2] - ball_pos) < gs.ROBOT_RADIUS * CLOSE_ENOUGH_FACTOR)

def test_charge_up_to():
    """ Tests charge_up_to in the trivial case of zero kick speed.
    Passes if charging finishes immediately.
    """
    simulator = Simulator("clear_field_test")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    charge = strategy.charge_up_to(1, 0.0)
    assert(charge)

def test_kick_ball():
    """Tests kick_ball to make sure it sets is_kicking to true"""
    simulator = Simulator("clear_field_test")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    strategy.kick_ball(1)
    commands = gs.get_robot_commands(team, 1)
    assert(commands.is_kicking)

def test_set_dribbler():
    """ Tests set_dribbler after setting to True and to False.
    Passes if it correctly returns the value that it is set to.
    """
    simulator = Simulator("clear_field_test")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    strategy.set_dribbler(1, True)
    commands = gs.get_robot_commands(team, 1)
    assert(commands.is_dribbling)
    strategy.set_dribbler(1, False)
    commands = gs.get_robot_commands(team, 1)
    assert(not commands.is_dribbling)

def test_stop():
    """ Tests stop function.
    Passes if robot has no waypoints and is set to be remain stationary.
    """
    simulator = Simulator("clear_field_test")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    strategy.path_find(1, [0, 0, 0])
    strategy.stop(1)
    commands = gs.get_robot_commands(team, 1)
    assert(not commands.waypoints)
    assert(commands._x == 0 and commands._y == 0 and commands._w == 0)

def test_move_straight():
    """ Tests move_straight on a clear field.
    Passes if the robot is given one waypoint at the destination.
    """
    goal_pos = [0, 1000, 0]
    simulator = Simulator("clear_field_test")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    strategy.path_find(1, goal_pos)
    waypoints = gs.get_robot_commands(team, 1).waypoints
    assert(len(waypoints) == 1 and (waypoints[0] == goal_pos).all())
    
def test_path_find_clear_field():
    """ Tests path_find when there is a clear path to the goal position.
    Passes if the robot is successfully directed to the goal.
    """
    simulator = Simulator("clear_field_test")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    strategy.path_find(1, [0, 0, 0])
    goal_pos = strategy.get_goal_pos(1)
    assert((goal_pos == [0, 0, 0]).all())

def test_path_find_surrounded():
    """ Tests path_find when the robot is surrounded by opponents and cannot find a path.
    Passes if the robot is not given any waypoints to try to reach this destination.
    """
    simulator = Simulator("surrounded_by_opponents_test")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    strategy.path_find(1, [0, 0, 0])
    goal_pos = strategy.get_goal_pos(1)
    assert(goal_pos is None)
    