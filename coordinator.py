from multiprocessing import Queue
from multiprocessing import Process, Event
import multiprocessing
import logging
from logging.handlers import SocketHandler
import signal
import time
from queue import Empty, Full


# Do not make this large or bad things will happen
MAX_Q_SIZE = 1

# Warning: This file is a pain in the ass as it deals with all of the multiprocessing.
# Only modify it as a last resort, or if you have a shittone of debugging time available.

class Provider(object):
    """
    Basic interface class that reads data in from the Coordinator, 
    does some action, and then writes actions back to the coordinator.  
    """
    def __init__(self):
        """
        Sets up queues for reading data in and out of this provider
        """
        from gamestate import GameState
        self.data_in_q = Queue(MAX_Q_SIZE)
        self.commands_out_q = Queue(MAX_Q_SIZE)
        self.gs = GameState()
        self.logger = None

        # Convenience variables for assess the performance of the provider
        self.last_run_time = None
        self.delta_time = None

        # This specifies the fields in the gamestate dict for which this
        # provider is the source of truth. These fields will be stored
        # locally, and not received from the coordinator or updated
        # in new gamestate packets.
        self._owned_fields = []

    def run(self):
        """
        Handle provider specific logic. This function is continuously repeatedly called AT MINIMUM
        once every second but likely much much more frequently. 
        It should modify self.gs which will be sent back to the coordinator.
        Needs to be implemented in child classes.
        """
        raise NotImplementedError("Need to implement run() in child classes.")

    def _update_gamestate(self):
        """
        Get the latest gamestate from the coordinator. Do not call this method from
        outside the provider.
        """
        # Save a copy of all of the fields this provider owns
        owned_field_values = dict()
        for field in self._owned_fields:
            owned_field_values[field] = getattr(self.gs, field)

        # Get a new gamestate copy from the coordinator
        try:
            self.gs = self.data_in_q.get(timeout=1)
        except Empty:
            pass

        # Restore the fields that this provider owns
        for key, value in owned_field_values.items():
            setattr(self.gs, key, value)

    def _send_result_back_to_coordinator(self):
        """
        Send the gamestate from the provider back to the coordinator.
        Do not call this method from outside the provider.
        """
        if self._owned_fields == []:
            return
        try:
            self.commands_out_q.put_nowait(self.gs)
        except Full:
            pass

    def _update_times(self):
        """
        Called every time run() completes. We record stuff here
        to monitor how our providers are performing.
        """
        t = time.time()
        if self.last_run_time:
            self.delta_time = self.last_run_time - t
        self.last_run_time = t

    def start_providing(self, stop_event):
        """
        Starts the provider. Should always be run on a background process.
        Usually this is called from Coordinator.start_game()
        """
        self.create_logger()
        try:
            self.pre_run()
            self._send_result_back_to_coordinator()
            while not stop_event.is_set():
                self._update_gamestate()
                self.run()
                self._update_times()
                self._send_result_back_to_coordinator()
        except:
            self.logger.exception("Fatal exception in provider %s", self.__class__.__name__)
        self.post_run()
        self.destroy()

    def pre_run(self):
        """
        This function is called exactly once whenever a provider is started, and before self.run() is called. 
        Override this function to do initialization that it wouldn't be possible to to in self.run() (which gets
        called repeatedly).
        """
        pass
    
    def post_run(self):
        """
        This function is called exactly once after the last iteratation of self.run() but before the
        provider is destroyed. Override this to do de-initialization.
        """
        pass

    def destroy(self):
        """
        Called by self.start_providing(). No need to call from anywhere else
        """
        self.destroy_queue(self.data_in_q)
        self.destroy_queue(self.commands_out_q)

    def destroy_queue(self, q):
        """
        Helper function for destroying multiprocessing.Queue objects
        """
        q.close()
        try:
            while True:
                item = q.get_nowait()
        except:
            pass
        q.join_thread()

    def create_logger(self, logger_name=None):
        if logger_name is None:
            logger_name = self.__class__.__name__
        self.logger = logging.getLogger(logger_name)
        self.logger.addHandler(logging.FileHandler('logs/%s.log' % logger_name, mode='w'))
        self.logger.setLevel(1)
        socket_handler = SocketHandler('127.0.0.1', 19996)
        self.logger.addHandler(socket_handler)
        self.logger.info("Created logger: %s" % logger_name)
        

class DisableSignals(object):
    """
    An object for disabling signals (SIGINT).

    Usage:

    with DisableSignals():
        # Do stuff here
    """
    def __enter__(self):
        self.default_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.default_handler)

class Coordinator(object):
    """
    A Coordinator object synchronises the entire game. It
    transfers data to and receives commands from all relevant
    parties including vision, refbox data, XBEE processes and
    strategy processes.
    """
    def __init__(self, 
                 providers):
        """
        Collects the objects to coordinate
        """
        from gamestate import GameState
        # A list of all of the provider that need to be synchronised
        self.providers = providers

        # Stores the processes currently in use by the coordinator
        self.processes = []

        # Can call create logger from init since we run Coordinator from the
        # main thread instead of separate process.
        self.create_logger()

        # The source of truth gamestate object
        self.gamestate = GameState()

        # This event is used to signal to the child processes when to stop
        self.stop_event = Event()

    def create_logger(self):
        self.logger = logging.getLogger('coordinator')
        self.logger.addHandler(logging.FileHandler('coordinator.log', mode='a'))
        self.logger.info("Initializing Coordinator")
        self.logger.setLevel(1)
        socket_handler = SocketHandler('0.0.0.0', 19996)
        self.logger.addHandler(socket_handler)
        self.logger.info("Created logger for coordinator")

    def start_game(self):
        """
        Starts all of the providers in their own processes..
        This should be called from main.py once a Coordinator has been instantiated
        """
        for provider in self.providers:
            self.processes.append(Process(target=provider.start_providing, args=[self.stop_event], name=provider.__class__.__name__))
            
        # Disable signals before fork so only parent process responds to SIGINT
        with DisableSignals():
            for proc in self.processes:
                self.logger.info("Starting process: %s", proc.name)
                proc.daemon = True
                proc.start()

        # Start main game loop
        self.logger.info("Starting main game loop")
        self.game_loop()
        
    def stop_game(self):
        """
        Sets the stop signal. Called from a signal handler in main.py.
        Causes both the game loop and all child processes to stop.
        """
        self.stop_event.set()

    def game_loop(self):
        """
        This is the main loop of the game that runs continuously in the main process.
        This should only be called from self.start_game()
        """
        while not self.stop_event.is_set():
            self.publish_new_gamestate()
            for provider in self.providers:
                self.get_data_from_provider(provider)

    def get_data_from_provider(self, provider):
        """
        Gets and integrates updated gamestate data from a provider's returned gamestate
        """
        provider_gs = self.get_from_provider_ignore_exceptions(provider)
        if provider_gs:
            for field in provider._owned_fields:
                setattr(self.gamestate, field, getattr(provider_gs, field))

    def publish_new_gamestate(self):
        """
        Pushes the current gamestate to the data_in_q of the providers that need it
        """
        for provider in self.providers:
            self.push_to_provider_ignore_exceptions(provider, self.gamestate)

    def push_to_provider_ignore_exceptions(self, provider, item):
        """
        A non-blocking helper method to .put() to a provider's 
        data_in_q queue and ignore any exceptions.
        
        Args:
            q (Provider): The provider in question

        Returns:
            The item from the queue, or None.
        """
        if not provider:
            return None
        q = provider.data_in_q
        try:
            q.put_nowait(item)
        except Full:
            # self.logger.warning("Push to provider had full queue")
            pass

    def get_from_provider_ignore_exceptions(self, provider):
        """
        A non-blocking helper method to .get() from a provider's 
        commands_out_q queue and ignore any exceptions.
        
        Args:
            q (Provider): The provider in question

        Returns:
            The item from the queue, or None.
        """
        if not provider:
            return None
        q = provider.commands_out_q
        try:
            item = q.get_nowait()
        except Empty:
            # self.logger.warning("Get from provider had empty queue")
            return None
        return item
        
        
