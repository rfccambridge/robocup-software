class Plays:
    """Full team role assignment for specific game cases. Used for very common
    plays that are called frequently no matter the game strategy."""

    def kickoff(self):
        # we tell robot 0 to follow our goalie function from roles.py
        self.goalie(1)
        # TODO: tell other robots to go to starting lineup
    
    def reset_game(self):
        raise NotImplementedError
    
    def halt(self):
        for robot_id in self.gs.get_robot_ids(self._team):
            self.stop(robot_id)

    def move_randomly(self):
         for robot_id in self.gs.get_robot_ids(self._team):
             self.random_robot(robot_id)

    def timeout(self) -> None:
        """Run a timeout play. All robots should stop whatever they're doing and
        immediate go out of bounds at coordinates:
            TODO: Add coordinates for timeout
        """

    
