class RobotCommands:
      def __init__(self):
            # each waypoint is (pos, speed)?
            self.waypoints = []
            self.dribbler_speed = 0
            self.charging = False
            self.kick = False

      def __str__(self):
            template = "waypoints: {}, dribbler_speed: {}, charging: {}, kick: {}"
            return template.format(self.waypoints, self.dribbler_speed, self.charging, self.kick)
