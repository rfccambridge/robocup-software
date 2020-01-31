# Role analysis class for strategy


class Coach:
    def __init__(self, strategy):
        self._strategy = strategy
        self._gs = strategy._gs

    def play(self):
        print("play")
#TODO store and examine different cases in gamestate
        if True:
            self._strategy.kickoff()
        else:
            pass
