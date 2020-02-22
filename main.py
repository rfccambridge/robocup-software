""" This is the control center, configures + launches all threads
    To run: python3 main.py
    (on Windows maybe just use: python main.py)
"""
import sys
import signal
import traceback
import argparse
import logging
import logging.handlers
import multiprocessing
import time

# http://plumberjack.blogspot.com/2010/09/using-logging-with-multiprocessing.html
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
    logging.basicConfig(level=logging_level, filename='robocup.log')
    # Welcome message
    print('RFC Cambridge Robocup Software')
    print('------------------------------')
    print('Running in simulator mode: {}'.format(IS_SIMULATION))
    if not IS_SIMULATION:
        print(f'Running in no radio mode: {NO_RADIO}')
    print(f'Running in no refbox mode: {NO_REFBOX}')

    # initialize gamestate + all other modules
    simulator = Simulator(SIMULATION_SETUP) 
    home_strategy = Strategy(HOME_TEAM, HOME_STRATEGY)
    visualization_provider = Visualizer()
    c = Coordinator(home_strategy, 
                    simulator, 
                    visualization_provider=visualization_provider)
    def stop_it(signum, frame):
        c.stop_game()
    signal.signal(signal.SIGINT, stop_it)
    c.start_game()
    sys.exit()
