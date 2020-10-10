# pylint: disable=import-error

try:
    from coach import Coach
except (SystemError, ImportError, ModuleNotFoundError):
    from .coach import Coach


class DefenseCoach(Coach):
    '''
    Class definition of a coach that is only concerned with defending
    '''

    def open_play(self):
        # Type your strategy here!
        raise NotImplementedError
