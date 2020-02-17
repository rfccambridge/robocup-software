""" This is the control center, configures + launches all threads
    To run: python3 main.py
    (on Windows maybe just use: python main.py)
"""
import sys
import signal
import traceback
import argparse
import logging
import time

logger = logging.getLogger(__name__)

# Remove pygame's annoying welcome message
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

from gamestate import GameState
from vision import SSLVisionDataProvider
from refbox import RefboxDataProvider
from strategy import Strategy
from visualization import Visualizer
from comms import Comms
from simulator import Simulator
from coordinator import Coordinator

# Setup command line arg parsing
parser = argparse.ArgumentParser(description='Runs our main codebase')
parser.add_argument('-s', '--simulate',
                    action="store_true",
                    help='run the codebase using the simulator rather than real vision data or robots')
parser.add_argument('-nra', '--no_radio',
                    action="store_true",
                    help='turns off command sending. no commands go over the radio')
parser.add_argument('-nre', '--no_refbox',
                    action="store_true",
                    help='ignores commands from the refbox.')
parser.add_argument('-d', '--debug',
                    action="store_true",
                    help='Uses more verbose logging for debugging.')
command_line_args = parser.parse_args()

# whether or not we are running with real field and robots
IS_SIMULATION = command_line_args.simulate
NO_RADIO = command_line_args.no_radio  # turns off command sending if real
NO_REFBOX = command_line_args.no_refbox # turns off refbox data provider
CONTROL_BOTH_TEAMS = False
# we will control home team in a real match
HOME_TEAM = 'blue'
AWAY_TEAM = 'yellow' if HOME_TEAM == 'blue' else 'blue'
# which simulator initial setup to use (if simulating)
SIMULATION_SETUP = 'full_teams'
# which strategies each team is running (see strategy module)
HOME_STRATEGY = 'defender_test'
AWAY_STRATEGY = None

# loop wait times for each thread - how much to sleep between loops
VISION_LOOP_SLEEP = .02
COMMS_SEND_LOOP_SLEEP = .1
COMMS_RECEIVE_LOOP_SLEEP = .1
CONTROL_LOOP_SLEEP = .1
SIMULATION_LOOP_SLEEP = .05
VISUALIZATION_LOOP_SLEEP = .05
GAME_LOOP_SLEEP = .1

if __name__ == '__main__':
    VERBOSE = False
    logging_level = logging.INFO
    if command_line_args.debug:
        logging_level = logging.DEBUG
    logging.basicConfig(level=logging_level)

    # Welcome message
    print('RFC Cambridge Robocup Software')
    print('------------------------------')
    print('Running in simulator mode: {}'.format(IS_SIMULATION))
    if not IS_SIMULATION:
        print(f'Running in no radio mode: {NO_RADIO}')
    print(f'Running in no refbox mode: {NO_REFBOX}')

    # initialize gamestate + all other modules
    simulator = Simulator(SIMULATION_SETUP) 
    home_strategy = Strategy(HOME_TEAM)
    visualization_provider = Visualizer()

    c = Coordinator(home_strategy, simulator, visualization_provider=visualization_provider)
    c.start_game()
    time.sleep(10)
    c.stop_game()
    exit() #testing only!!!!!
    # choose which modules to run based on run conditions
    logger.info('Spinning up Threads...')
    if IS_SIMULATION:
        # spin up simulator to replace actual vision data + comms
        if not NO_REFBOX:
            refbox.start_updating(VISION_LOOP_SLEEP)
    else:
        # spin up ssl-vision data polling to update gamestate
        vision.start_updating(VISION_LOOP_SLEEP)
        if not NO_RADIO:
            # spin up comms to send commands to robots
            home_comms.start_sending(COMMS_SEND_LOOP_SLEEP)
            # home_comms.start_receiving(COMMS_RECEIVE_LOOP_SLEEP)
            if CONTROL_BOTH_TEAMS:
                away_comms.start_sending(COMMS_SEND_LOOP_SLEEP)
                # away_comms.start_sending(COMMS_RECEIVE_LOOP_SLEEP)
        if not NO_REFBOX:
            refbox.start_updating(VISION_LOOP_SLEEP)
    # spin up strategy threads to control the robots
    home_strategy.start_controlling(HOME_STRATEGY, CONTROL_LOOP_SLEEP)
    if CONTROL_BOTH_TEAMS:
        away_strategy.start_controlling(AWAY_STRATEGY, CONTROL_LOOP_SLEEP)
    # initialize visualizer to show robots on screen
    visualizer = Visualizer(gamestate, home_strategy, away_strategy)
    # start the game  - now everything should be going
    gamestate.start_game(GAME_LOOP_SLEEP)

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
        refbox.stop_updating()
        home_comms.stop_sending_and_receiving()
        away_comms.stop_sending_and_receiving()
        simulator.stop_simulating()
        home_strategy.stop_controlling()
        away_strategy.stop_controlling()
        gamestate.end_game()
        print('Done Cleaning Up All Threads')
        sys.exit()
    signal.signal(signal.SIGINT, exit_gracefully)

    print('Running! Ctrl-c repeatedly to quit (C-c-k on eshell?!)')

    # (visualizer runs on main thread to work on all platforms)
    visualizer.visualization_loop(VISUALIZATION_LOOP_SLEEP)
    traceback.print_stack()
