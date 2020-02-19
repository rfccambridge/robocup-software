from multiprocessing import Queue
from multiprocessing import Process, Event
import multiprocessing
from gamestate import GameState
import logging
import signal

logger = logging.getLogger(__name__)

stop_event = Event()

class Provider(object):
    """
    Basic interface class that reads data in from the Coordinator, 
    does some action, and then writes actions back to the coordinator.  
    """
    def __init__(self):
        default_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGINT, default_handler)
        self.data_in_q = Queue()
        self.commands_out_q = Queue()
        self.stop_event = stop_event

    def run(self):
        """
        Handle provider specific logic. Should accept data from
        self.data_in_q and write outputs to self.commands_out_q.
        Needs to be implemented in child classes. Should be a loop that
        runs forever (while True)
        
        Raises:
            NotImplementedError: You forgot to implement this in child classes

        Args:
            exit_event : multiprocessing.Event. Indicates whether the provider should exit or not
        """
        raise NotImplementedError("Need to implement run() in child classes.")

    def start_providing(self):
        self.pre_run()
        while not self.stop_event.is_set():
            self.run()
        self.post_run()
        self.destroy()

    def pre_run(self):
        pass
    
    def post_run(self):
        print("POST RUN")

    def destroy(self):
        # self.destroy_queue(self.data_in_q)
        # self.destroy_queue(self.commands_out_q)
        print(f'DESTROYING {multiprocessing.current_process().pid}')

    def destroy_queue(self, q):
        q.close()
        try:
            while True:
                print('in here')
                item = q.get_nowait()
        except:
            pass
        print('waitingt for q join')
        q.join_thread()
        print('q joinged')
        


    
class Coordinator(object):
    """
    A Coordinator object synchronises the entire game. It
    transfers data to and receives commands from all relevant
    parties including vision, refbox data, XBEE processes and
    strategy processes.
    """
    def __init__(self, 
                 yellow_strategy: Provider,
                 vision_provider : Provider,
                 yellow_radio_provider: Provider = None,
                 refbox_provider: Provider = None,
                 blue_strategy: Provider = None,
                 blue_radio_provider: Provider = None,
                 visualization_provider: Provider = None):
        """
        Collects the objects to coordinate
        """
        self.vision_provider = vision_provider
        self.yellow_radio_provider = yellow_radio_provider
        self.refbox_provider = refbox_provider
        self.yellow_strategy = yellow_strategy
        self.blue_strategy = blue_strategy
        self.blue_radio_provider = blue_radio_provider
        self.visualization_provider = visualization_provider

        # Stores the processes currently in use by the coordinator
        self.processes = []

        self.gamestate = GameState()


    def start_game(self):
        default_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.processes.append(Process(target=self.vision_provider.start_providing))
        self.processes.append(Process(target=self.yellow_strategy.start_providing))
        # if self.blue_strategy:
        #     self.processes.append(Process(target=self.blue_strategy.run, args=[self.exit_event]))
        # if self.blue_radio_provider:
        #     self.processes.append(Process(target=self.blue_radio_provider.run, args=[self.exit_event]))
        # if self.refbox_provider:
        #     self.processes.append(Process(target=self.refbox_provider.run, args=[self.exit_event]))        
        # if self.yellow_radio_provider:
        #     self.processes.append(Process(target=self.yellow_radio_provider.run, args=[self.exit_event]))
        if self.visualization_provider:
            self.processes.append(Process(target=self.visualization_provider.start_providing))
        print(f'vision === pid == {self.processes[0]}')
        print(f'yellow strategy === pid == {self.processes[1]}')
        print(f'visualization provider === pid == {self.processes[2]}')
        for proc in reversed(self.processes):
            proc.daemon = True
            proc.start()
        signal.signal(signal.SIGINT, default_handler)
        self.game_loop()
        
    def stop_game(self):
        stop_event.set()
        print('Setting exit event')

    def game_loop(self):
        # Need to push in a gamestate object initially
        self.vision_provider.data_in_q.put_nowait(self.gamestate)
        while not stop_event.is_set():
            self.update_vision_data()
            self.refbox_data = self.get_updated_refbox_data()
            self.publish_new_gamestate()
            self.update_robot_commands()
            self.publish_robot_commands()
        print('finished game_loop')

    def update_vision_data(self):
        """
        Gets updated vision data from either SSLVision or the simulator
        """
        try:
            self.gamestate = self.vision_provider.commands_out_q.get_nowait()
        except:
            pass

    def get_updated_refbox_data(self):
        """
        Gets updated refbox data if 
        """
        if not self.refbox_provider:
            return None
        return self.refbox_provider.commands_out_q.get_nowait()

    def publish_robot_commands(self):
        # send robot commands to xbee here
        # or to simulator
        if self.blue_radio_provider:
            try:
                return self.blue_radio_provider.data_in_q.put_nowait(self.gamestate)
            except:
                pass
        if self.yellow_radio_provider:
            try:
                return self.yellow_radio_provider.data_in_q.put_nowait(self.gamestate)
            except:
                pass

    def publish_new_gamestate(self):
        try:
            if self.blue_strategy:
                self.blue_strategy.data_in_q.put_nowait(self.gamestate)
        except:
            # Likely queue is full
            pass
        try:
            self.yellow_strategy.data_in_q.put_nowait(self.gamestate)
        except:
            # Likely queue is full 
            pass
        try:
            self.vision_provider.data_in_q.put_nowait(self.gamestate)
        except:
            pass
        try:
            if self.visualization_provider:
                self.visualization_provider.data_in_q.put_nowait(self.gamestate)
        except:
            pass

    def update_robot_commands(self):
        try:
            if self.blue_strategy:
                self.gamestate._blue_robot_commands = self.blue_strategy.commands_out_q.get_nowait()
        except:
            # Likely queue is empty
            pass
        try:
            self.gamestate._yellow_robot_commands = self.yellow_strategy.commands_out_q.get_nowait()
        except:
            # Likely queue is empty
            pass
        