import sys
import signal

from gamestate import GameState
from vision import SSLVisionDataProvider
from strategy import Strategy
from visualization import Visualizer
from comms import Comms
from simulator import Simulator

# whether or not we are running with real field and robots
IS_REAL = False

if __name__ == '__main__':
    VERBOSE = False

    # initialize gamestate + all other modules
    gamestate = GameState()
    visualizer = Visualizer(gamestate)
    vision = SSLVisionDataProvider(gamestate)
    comms = Comms(gamestate, 'blue')
    simulator = Simulator(gamestate)
    strategy = Strategy(gamestate, 'blue')

    # choose which modules to actually run
    print('Spinning up Threads...')
    if IS_REAL:
        # spin up ssl-vision data polling to update gamestate
        vision.start_updating()
        # spin up comms to send commands to robots
        comms.start_sending()
        # comms.start_receiving()
    else:
        # spin up simulator to replace actual vision data + comms
        simulator.start_simulating()
        
    gamestate.start_analyzing()
    strategy.start_controlling()

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
        comms.stop_sending_and_receiving()
        simulator.stop_simulating()
        gamestate.stop_analyzing()
        strategy.stop_controlling()
        print('Done Cleaning Up All Threads')
        sys.exit()
    signal.signal(signal.SIGINT, exit_gracefully)

    print('Running! Ctrl-c repeatedly to quit')

    # spin up visualization to show robots on screen
    # (runs on main thread to work on all platforms)
    visualizer.visualization_loop()

# import logging
# logging.basicConfig(level=logging.WARNING)

# import traceback
#    try:
#    except Exception:
#        print('Unexpected Error!')
#        print(traceback.format_exc())
