import sys
import signal
import traceback
import time
import logging

from gamestate import GameState
from vision import SSLVisionDataProvider
from strategy import Strategy
from visualization import Visualizer
from comms import Comms
from simulator import Simulator

# whether or not we are running with real field and robots
IS_REAL = False

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
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
    gamestate.start_analyzing()
    # spin up visualization to show robots on screen
    visualizer.start_visualizing()
    if IS_REAL:
        # spin up ssl-vision data polling to update gamestate
        vision.start_updating()
        # spin up comms to send commands to robots
        comms.start_sending()
        # comms.start_receiving()
    else:
        # spin up simulator to replace actual vision data + comms
        simulator.start_simulating()
        #simulator.put_fake_ball((0, 0))
        #simulator.put_fake_robot('blue', 8, (100, 100, 0))
        simulator.initialize_ball_move()
    
    # intialize algorithm module
    strategy = Strategy(gamestate, 'blue')

    goal_x = 3000
    goal_y = 1000

    exit_signal_received = False
    def exit_gracefully(signum, frame):
        global exit_signal_received
        if exit_signal_received:
            return
        else:
            exit_signal_received = True
        print('Exiting Everything')
        # clean up all threads
        gamestate.stop_analyzing()
        visualizer.stop_visualizing()
        vision.stop_updating()
        comms.stop_sending_and_receiving()
        simulator.stop_simulating()
        print('Done Cleaning Up All Threads')
        sys.exit()
    signal.signal(signal.SIGINT, exit_gracefully)

    print('Running! Ctrl-c repeatedly to quit')

    try:
        while True:
            # make sure prints from all threads get flushed to terminal
            sys.stdout.flush()
            # set goal pos to click location on visualization window
            if visualizer.user_click_field:
                goal_x, goal_y = visualizer.user_click_field

            # tell robot to go straight towards goal position
            strategy.move_straight(8, (goal_x, goal_y, 0))
            # TO TEST: tell robot to greedily pathfind to goal position
            # TODO: discuss parameters + more advanced pathfinding options: 
            # A*, time projection, RRT (see old c# codebase)
            # strategy.greedy_path_find(8, (goal_x, goal_y))

            # yield to other threads
            time.sleep(0.05)
    except Exception:
        print('Unexpected Error!')
        print(traceback.format_exc())
