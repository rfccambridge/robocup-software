class Plays:
    """Full team role assignment for specific game cases. Used for very common
    plays that are called frequently no matter the game strategy."""

    def kickoff(self):
        # we tell robot 0 to follow our goalie function from roles.py
        self.goalie(1)
        # TODO: tell other robots to go to starting lineup


    def timeout(self) -> None:
        """Run a timeout play. All robots should stop whatever they're doing and
        immediate go out of bounds at coordinates:
            TODO: Add coordinates for timeout
        """

    
