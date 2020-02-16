from multiprocessing import Queue

class Provider(object):
    def __init__(self):
        self.data_in_q = Queue()
        self.commands_out_q = Queue()
    
    def run(self):
        raise NotImplementedError
    
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
                 radio_provider: Provider =None,
                 refbox_provider: Provider =None,
                 blue_strategy: Provider =None):
        """
        Collects the objects to coordinate
        """
        self.vision_provider = vision_provider
        self.radio_provider = radio_provider
        self.refbox_provider = refbox_provider
        self.yellow_strategy = yellow_strategy
        self.blue_strategy = blue_strategy

        self.is_playing = False

        # Commands data (desired robot actions)
        self.robot_commands = dict()

        # This stores the global state of the game
        self.game_data = dict()

        # Stores the processes currently in use by the coordinator
        self.processes = []

    def start_game(self):
        self.processes.append(Process(target=self.vision_provider.run))
        self.processes.append(Process(target=self.yellow_strategy.run))
        if self.blue_strategy:
            self.processes.append(Process(target=self.blue_strategy.run))
        if self.refbox_provider:
            self.processes.append(Process(target=self.refbox_provider.run))        
        if self.radio_provider:
            self.processes.append(Process(target=self.radio_provider.run))
        
    def stop_game(self):
        for proc in self.processes:
            proc.terminate()

    def game_loop(self):
        while self.is_playing:
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
        return self.refbox_provider.commands_out_q.get()

    def publish_robot_commands(self):
        # send robot commands to xbee here
        # or to simulator
        return self.radio_provider.data_in_q.put(self.robot_commands)

    def publish_new_gamestate(self):
        try:
            self.blue_gamestate_queue.put_nowait(snapshot)
        except:
            # Likely queue is full
            pass
        try:
            self.yellow_gamestate_queue.put_nowait(snapshot)
        except:
            # Likely queue is full 
            pass
    
    def update_robot_commands(self):
        try:
            self._blue_robot_commands = self.blue_commands_queue.get_nowait()
        except:
            # Likely queue is empty
            pass
        try:
            self._yellow_robot_commands = self.yellow_commands_queue.get_nowait()
        except:
            # Likely queue is empty
            pass
        
    def snapshot_gamedata(self):
        d = {}
        d['vision_data'] = self.some_vision_data
        return d

    def clean_up(self):
        self.yellow_strategy_process.terminate()
        self.blue_strategy_process.terminate()
