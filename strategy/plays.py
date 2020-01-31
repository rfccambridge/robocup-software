class Plays:
    """Full team role assignment for specific game cases"""

    def kickoff(self):
        # we tell robot 0 to follow our goalie function from roles.py
        self.goalie(1)
