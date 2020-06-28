""" This is the control center, configures + launches all threads
    To run: python3 main.py
    (on Windows maybe just use: python main.py)
"""
import sys
import signal
import argparse
import logging
import logging.handlers
from vision import SSLVisionDataProvider
from refbox import RefboxDataProvider
from strategy import Strategy
from visualization import Visualizer
from comms import Comms
from simulator import Simulator
from coordinator import Coordinator
import os

# Remove pygame's annoying welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# http://plumberjack.blogspot.com/2010/09/using-logging-with-multiprocessing.html
logger = logging.getLogger(__name__)


# Setup command line arg parsing
parser = argparse.ArgumentParser(description='Runs our main codebase')
parser.add_argument('-s', '--simulate',
                    action="store_true",
                    help='run the codebase using the simulator rather than '
                         'real vision data or robots')
parser.add_argument('-ss', '--simulator_setup',
                    default='full_teams',
                    help='The setup to use for the simulator.')
parser.add_argument('-nra', '--no_radio',
                    action="store_true",
                    help='Turns off command sending. No cmds go over radio.')
parser.add_argument('-nre', '--no_refbox',
                    action="store_true",
                    help='Ignores commands from the refbox.')
parser.add_argument('-cbt', '--control_both_teams',
                    action="store_true",
                    help='Indicates that we are playing against ourselves so '
                         'we should play as both teams.')
parser.add_argument('-htc', '--home_team_color',
                    choices=['yellow', 'blue'],
                    default='blue',
                    help="The color of the home team.")
parser.add_argument('-hs', '--home_strategy',
                    default='UI',
                    help="The strategy the home team should use to play.")
parser.add_argument('-as', '--away_strategy',
                    default='UI',
                    help="The strategy the away team should use to play.")
parser.add_argument('-d', '--debug',
                    action="store_true",
                    help='Uses more verbose logging for debugging.')
command_line_args = parser.parse_args()

# Create globals
IS_SIMULATION = command_line_args.simulate
NO_RADIO = command_line_args.no_radio
NO_REFBOX = command_line_args.no_refbox
CONTROL_BOTH_TEAMS = command_line_args.control_both_teams
HOME_TEAM = command_line_args.home_team_color
AWAY_TEAM = 'yellow' if HOME_TEAM == 'blue' else 'blue'
SIMULATOR_SETUP = command_line_args.simulator_setup
HOME_STRATEGY = command_line_args.home_strategy
AWAY_STRATEGY = command_line_args.away_strategy


def setup_logging():
    logging_level = logging.INFO
    if command_line_args.debug:
        logging_level = logging.DEBUG
    logging.basicConfig(level=logging_level, filename='robocup.log')


if __name__ == '__main__':
    setup_logging()

    # Welcome message
    print('RFC Cambridge Robocup Software')
    print('------------------------------')
    print(f'Running in simulator mode: {IS_SIMULATION}')
    print(f'Running in no radio mode: {NO_RADIO}')
    print(f'Running in no refbox mode: {NO_REFBOX}')
    print('Open cutelog separately to see logging!')

    # Initialize providers and pass to coordinator
    providers = []

    if IS_SIMULATION:
        NO_RADIO = True
        providers += [Simulator(SIMULATOR_SETUP)]
    else:
        providers += [SSLVisionDataProvider()]

    if not NO_REFBOX:
        providers += [RefboxDataProvider()]

    if not NO_RADIO:
        providers += [Comms(HOME_TEAM)]
        if CONTROL_BOTH_TEAMS:
            providers += [Comms(AWAY_TEAM, True)]

    providers += [Strategy(HOME_TEAM, HOME_STRATEGY)]

    if CONTROL_BOTH_TEAMS:
        providers += [Strategy(AWAY_TEAM, AWAY_STRATEGY)]

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
