"""
Contains information about a robot's state that we don't directly control.
For example, the kicker charge level or other sensor data.
Populated by feedback from radio or simulator.
"""


class RobotStatus:
    # Robot Constants
    MAX_KICK_SPEED = 2500  # TODO
    MAX_CHARGE_LEVEL = 250  # volts? should be whatever the board measures in
    CHARGE_RATE = 60  # volts per second?

    def __init__(self):
        self.charge_level = 0
        self.logger = None

    # clears out charge as though we kicked
    def simulate_kick(self):
        self.charge_level = 0

    # estimate increase in charge level based on time elapsed
    def simulate_charge(self, delta_time):
        self.charge_level += delta_time * self.CHARGE_RATE
        if self.charge_level > self.MAX_CHARGE_LEVEL:
            self.charge_level = self.MAX_CHARGE_LEVEL

    def kick_velocity(self):
        # TODO: more accurate using voltage
        speed_factor = self.charge_level / self.MAX_CHARGE_LEVEL
        return self.MAX_KICK_SPEED * speed_factor
