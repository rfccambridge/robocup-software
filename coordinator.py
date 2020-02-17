from multiprocessing import Queue
from multiprocessing import Process
from gamestate import GameState
import logging

logger = logging.getLogger(__name__)

class Provider(object):
    """
    Basic interface class that reads data in from the Coordinator, 
    does some action, and then writes actions back to the coordinator.  
    """
    def __init__(self):
        self.data_in_q = Queue()
        self.commands_out_q = Queue()
    
    def run(self):
        """
        Handle provider specific logic. Should accept data from
        self.data_in_q and write outputs to self.commands_out_q.
        Needs to be implemented in child classes. Should be a loop that
        runs forever (while True)
        
        Raises:
            NotImplementedError: You forgot to implement this in child classes
        """
        raise NotImplementedError("Need to implement run() in child classes.")
    
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
                 blue_radio_provider: Provider = None):
        """
        Collects the objects to coordinate
        """
        self.vision_provider = vision_provider
        self.yellow_radio_provider = yellow_radio_provider
        self.refbox_provider = refbox_provider
        self.yellow_strategy = yellow_strategy
        self.blue_strategy = blue_strategy
        self.blue_radio_provider = blue_radio_provider

        # Stores the processes currently in use by the coordinator
        self.processes = []

        self.gamestate = GameState() 

    def start_game(self):
        self.processes.append(Process(target=self.vision_provider.run))
        self.processes.append(Process(target=self.yellow_strategy.run))
        if self.blue_strategy:
            self.processes.append(Process(target=self.blue_strategy.run))
        if self.blue_radio_provider:
            self.processes.append(Process(target=self.blue_radio_provider.run))
        if self.refbox_provider:
            self.processes.append(Process(target=self.refbox_provider.run))        
        if self.yellow_radio_provider:
            self.processes.append(Process(target=self.yellow_radio_provider.run))
        
        for proc in self.processes:
            proc.start()
        
    def stop_game(self):
        for proc in self.processes:
            proc.terminate()

    def game_loop(self):
        # Need to push in a gamestate object initially
        self.vision_provider.data_in_q.put_nowait(self.gamestate)
        while True:
            self.vision_data = self.get_updated_vision_data()
            self.refbox_data = self.get_updated_refbox_data()
            self.publish_new_gamestate()
            self.update_robot_commands()
            self.publish_robot_commands()

    def get_updated_vision_data(self):
        """
        Gets updated vision data from either SSLVision or the simulator
        """
        return self.vision_provider.commands_out_q.get()

    def get_updated_refbox_data(self):
        """
        Gets updated refbox data if 
        """
        if not self.refbox_provider:
            return None
        return self.refbox_provider.commands_out_q.get()

    def publish_robot_commands(self):
        # send robot commands to xbee here
        # or to simulator
        if self.blue_radio_provider:
            try:
                return self.blue_radio_provider.data_in_q.put(self.robot_commands)
            except:
                pass
        if self.yellow_radio_provider:
            try:
                return self.yellow_radio_provider.data_in_q.put(self.robot_commands)
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
        
    def clean_up(self):
        for proc in self.processes:
            proc.terminate()