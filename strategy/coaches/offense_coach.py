# pylint: disable=import-error

try:
    from coach import Coach
except (SystemError, ImportError, ModuleNotFoundError):
    from .coach import Coach


class OffenseCoach(Coach):
    '''
    Class definition of a coach that is only concerned with attacking
    '''

    def open_play(self):
        # Type your strategy here!
        raise NotImplementedError
