from ..actions import Actions
from ..strategy import Strategy

from simulator.simulator import Simulator

team = "blue"
strategy_name = ""

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
    