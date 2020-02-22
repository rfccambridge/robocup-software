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
parser.add_argument('-cbt', '--control_both_teams',
                    action="store_true",
                    help='indicates that we are playing against ourselves and so we should play as both teams.')
parser.add_argument('-d', '--debug',
                    action="store_true",
                    help='Uses more verbose logging for debugging.')
command_line_args = parser.parse_args()

# whether or not we are running with real field and robots
IS_SIMULATION = command_line_args.simulate
NO_RADIO = command_line_args.no_radio  # turns off command sending if real
NO_REFBOX = command_line_args.no_refbox # turns off refbox data provider
CONTROL_BOTH_TEAMS = command_line_args.control_both_teams
# we will control home team in a real match
HOME_TEAM = 'blue'
AWAY_TEAM = 'yellow' if HOME_TEAM == 'blue' else 'blue'
# which simulator initial setup to use (if simulating)
SIMULATION_SETUP = 'full_teams'
# which strategies each team is running (see strategy module)
HOME_STRATEGY = 'defender_test'
AWAY_STRATEGY = None

if __name__ == '__main__':
    VERBOSE = False
    logging_level = logging.INFO
    if command_line_args.debug:
        logging_level = logging.DEBUG
    logging.basicConfig(level=logging_level, filename='robocup.log')
    # Welcome message
    print('RFC Cambridge Robocup Software')
    print('------------------------------')
    print(f'Running in simulator mode: {IS_SIMULATION}')
    print(f'Running in no radio mode: {NO_RADIO}')
    print(f'Running in no refbox mode: {NO_REFBOX}')

    # Initialize providers and pass to coordinator
    providers = []
    
    if IS_SIMULATION:
        NO_RADIO = True
        providers += [Simulator(SIMULATION_SETUP)] 

    if not NO_REFBOX:
        providers += [RefboxDataProvider()]

    if not NO_RADIO:
        providers += [Comms(HOME_TEAM)]
        providers += [Comms(AWAY_TEAM, True)]

    providers += [Strategy(HOME_TEAM)]

    if CONTROL_BOTH_TEAMS:
        providers += [Strategy(AWAY_TEAM)]
    
    providers += [Visualizer()]

    # Pass the providers to the coordinator
    c = Coordinator(providers)

    # Setup the exit handler
    def stop_it(signum, frame):
        c.stop_game()
    signal.signal(signal.SIGINT, stop_it)
    
    # Start the game
    c.start_game()

    # Exit once game is over
    sys.exit()
