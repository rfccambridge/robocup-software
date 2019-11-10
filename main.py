import sys
import signal

from gamestate import GameState
from vision import SSLVisionDataProvider
from strategy import Strategy
from visualization import Visualizer
from comms import Comms
from simulator import Simulator

# whether or not we are running with real field and robots
IS_SIMULATION = False
CONTROL_BOTH_TEAMS = False
# we will control home team in a real match
HOME_TEAM = 'blue'
AWAY_TEAM = 'yellow' if HOME_TEAM == 'blue' else 'blue'

if __name__ == '__main__':
    VERBOSE = False

    # initialize gamestate + all other modules
    gamestate = GameState()
    vision = SSLVisionDataProvider(gamestate)
    home_comms = Comms(gamestate, HOME_TEAM)
    away_comms = Comms(gamestate, AWAY_TEAM, True)
    simulator = Simulator(gamestate)
    home_strategy = Strategy(gamestate, HOME_TEAM)
    away_strategy = Strategy(gamestate, AWAY_TEAM)

    # choose which modules to run based on run conditions
    print('Spinning up Threads...')
    if not IS_SIMULATION:
        # spin up ssl-vision data polling to update gamestate
        vision.start_updating()
        # spin up comms to send commands to robots
        home_comms.start_sending()
        # comms.start_receiving()
        if CONTROL_BOTH_TEAMS:
            away_comms.start_sending()
    else:
        # spin up simulator to replace actual vision data + comms
        simulator.start_simulating()

    gamestate.start_analyzing()
    home_strategy.start_controlling()
    if CONTROL_BOTH_TEAMS:
        away_strategy.start_controlling()

    # Prepare to be interrupted by user
    exit_signal_received = False

    def exit_gracefully(signum, frame):
        global exit_signal_received
        if exit_signal_received:
            return
        else:
            exit_signal_received = True
        print('Exiting Everything')
        # clean up all threads
        vision.stop_updating()
        home_comms.stop_sending_and_receiving()
        away_comms.stop_sending_and_receiving()
        simulator.stop_simulating()
        gamestate.stop_analyzing()
        home_strategy.stop_controlling()
        away_strategy.stop_controlling()
        print('Done Cleaning Up All Threads')
        sys.exit()
    signal.signal(signal.SIGINT, exit_gracefully)

    print('Running! Ctrl-c repeatedly to quit')

    # run visualization to show robots on screen
    visualizer = Visualizer(gamestate, home_strategy, away_strategy)
    # (runs on main thread to work on all platforms)
    visualizer.visualization_loop()

# import logging
# logging.basicConfig(level=logging.WARNING)

# import traceback
#    try:
#    except Exception:
#        print('Unexpected Error!')
#        print(traceback.format_exc())
