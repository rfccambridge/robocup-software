import math
from comms.robot_commands import RobotCommands

rc = RobotCommands()

# trim angle helpers
def test_trim_angle():
    angle = math.pi + 1
    assert rc.trim_angle(angle) == -1 * (math.pi - 1)

# serialize/deserialize conversion
# robot/field perspective conversion
# append waypoint works (whether or not w is None)
# same with set waypoints^

# predict pos is reasonable when there is 1 waypoint, 2 waypoints, or none
# derive waypoints is reasonable ^, also with varying direction change. 

# what do to about magnitude?

# urgent waypoint nearby, see max speed


