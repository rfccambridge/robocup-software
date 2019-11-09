try:
    from comms import Comms
    from robot_commands import RobotCommands
except (SystemError, ImportError):
    from .comms import Comms
    from .robot_commands import RobotCommands
