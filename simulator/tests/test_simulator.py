"""Makes sure that the simulator setup actually works and isn't
broken by any new changes."""
from ..simulator import Simulator


def test_simulator_startup():
    sim = Simulator("full_teams")
    sim.pre_run()
    assert True


def test_simulator_moving_ball():
    sim = Simulator("moving_ball")
    sim.pre_run()
    assert True


def test_simulator_entryvid():
    sim = Simulator("entry_video")
    sim.pre_run()
    assert True
