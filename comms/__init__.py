try:
    from comms import Comms
    from robot_commands import RobotCommands
    from robot_status import RobotStatus
except (SystemError, ImportError):
    from .comms import Comms
    from .robot_commands import RobotCommands
    from .robot_status import RobotStatus
