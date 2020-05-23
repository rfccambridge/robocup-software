from ..actions import Actions
from ..strategy import Strategy

from simulator.simulator import Simulator

team = "blue"
strategy_name = ""

def test_path_find():
    simulator = Simulator("full_teams")
    simulator.pre_run()
    gs = simulator.gs
    strategy = Strategy(team, strategy_name)
    strategy.gs = gs
    print(gs.get_robot_position(team, 1))
    strategy.path_find(1, [0, 0, 0])
    print(strategy.gs.get_robot_commands(team, 1))
    assert(False)
    