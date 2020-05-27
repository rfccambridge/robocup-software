import numpy as np
import math
from comms.robot_commands import RobotCommands

# trim angle helpers
def test_trim_angle():
    rc = RobotCommands()
    angle = math.pi + 1
    assert rc.trim_angle(angle) == -1 * (math.pi - 1)
    angle = -1 * math.pi - 1
    assert rc.trim_angle(angle) == math.pi - 1
    angle = 2 * math.pi
    assert rc.trim_angle(angle) == 0

def test_trim_angle_90():
    rc = RobotCommands()
    angle = math.pi / 2 + 1
    assert rc.trim_angle_90(angle) == -1 * (math.pi / 2 - 1)
    angle = -1 * math.pi/2 - 1
    assert rc.trim_angle_90(angle) == math.pi/2 - 1
    angle = math.pi
    assert rc.trim_angle_90(angle) == 0

# serialize/deserialize conversion
def test_command_serialization():
    def construct_rc(is_dribbling, is_charging, is_kicking, x, y, w):
        commands = RobotCommands()
        commands.is_dribbling = is_dribbling
        commands.is_charging = is_charging
        commands.is_kicking = is_kicking
        commands.set_speeds(x, y, w)
        return commands
    # round movement values due to serialization granularity errors
    def round_command(cmd_dict):
        def round_value(value, unit):
            return (value + unit / 2.0) // unit * unit
        # x and y are to the nearest 20 mm/s
        cmd_dict['x'] = round_value(cmd_dict['x'], 20)
        cmd_dict['y'] = round_value(cmd_dict['y'], 20)
        # w to the nearest .2 radians/s
        cmd_dict['w'] = round_value(cmd_dict['w'], .1)
    # see if serializing then deserializing retains approx values
    def assert_serialize(is_dribbling, is_charging, is_kicking, x, y, w):
        correct_cmd = {
            'is_dribbling': is_dribbling,
            'is_charging': is_charging,
            'is_kicking': is_kicking,
            'x': x,
            'y': y,
            'w': w,
            'robot_id': 0
        }
        rc = construct_rc(is_dribbling, is_charging, is_kicking, x, y, w)
        serialized_cmd = rc.get_serialized_command(0)
        deserialized_cmd = rc.deserialize_command(serialized_cmd)
        round_command(deserialized_cmd)
        round_command(correct_cmd)
        assert correct_cmd == deserialized_cmd
    assert_serialize(False, False, False, 0, 0, 0)
    assert_serialize(True, True, True, 100, 100, 2)
    assert_serialize(False, True, False, -20, 300, -2)
    assert_serialize(False, True, False, -200, 500, 0)

# robot/field perspective conversion helpers
def test_perspective_conversion():
    rc = RobotCommands()
    def assert_conversion(w_robot, vector):
        ftr = rc.field_to_robot_perspective(w_robot, vector)
        rtf = rc.robot_to_field_perspective(w_robot, vector)
        assert np.allclose(rc.field_to_robot_perspective(w_robot, rtf), vector)
        assert np.allclose(rc.robot_to_field_perspective(w_robot, ftr), vector)
    assert_conversion(0, np.array([0, 0]))
    assert_conversion(0, np.array([100, 0]))
    assert_conversion(0, np.array([0, 100]))
    assert_conversion(math.pi, np.array([0, 100]))
    assert_conversion(-math.pi, np.array([20, 100]))
    assert_conversion(-math.pi, np.array([-200, 50]))
    assert_conversion(-math.pi + 1, np.array([-200, -150]))
    # also check a specific case
    ftr = rc.field_to_robot_perspective(0, np.array([100, 0]))
    assert np.allclose(ftr, np.array([0, 100]))
    ftr = rc.field_to_robot_perspective(math.pi / 2, np.array([100, 0]))
    assert np.allclose(ftr, np.array([100, 0]))
    ftr = rc.field_to_robot_perspective(math.pi / 2, np.array([100, 100]))
    assert np.allclose(ftr, np.array([100, 100]))
    
def test_append_waypoint():
    rc = RobotCommands()
    waypoints = [
        np.array([100, 0, 0]),
        np.array([100, 100, 0]),
        np.array([0, 100, 0]),
        np.array([0, 0, 0]),
    ]
    current_position = np.array([0, 0, 0])
    for i, wp in enumerate(waypoints):
        rc.append_waypoint(wp, current_position)
        assert (len(rc.waypoints) == i + 1) and np.allclose(rc.waypoints[-1], wp)
    # make sure it can handle None for w
    rc.append_waypoint([-100, -100, None], current_position)
    assert (len(rc.waypoints) == len(waypoints) + 1) and \
        (rc.waypoints[-1][2] is not None)

# tests the basic functionality fo derive_speeds
# just looks at basic directionality, not reducing speed for turns
# so, logic can be improved (made smoother) without breaking this test
def test_derive_speeds():
    rc = RobotCommands()
    angle = math.pi / 2 # makes robot perspective same as field - easier
    original_position = np.array([0, 0, angle])
    waypoints = [
        np.array([1000, 0, angle]),
        np.array([1000, 1000, angle]),
        np.array([0, 1000, angle]),
        np.array([0, 0, angle]),
        np.array([0, -1000, angle + 1]),
    ]
    # no waypoints do nothing
    rc.derive_speeds(original_position)
    assert rc._x == 0 and rc._y ==0 and rc._w == 0
    # now test deriving speeds from waypoints
    rc.waypoints = waypoints
    rc.derive_speeds(original_position)
    assert rc._x > 0 and np.allclose(rc._y, 0)
    # pretend to arrive at each waypoint and rederive speeds
    rc.derive_speeds(waypoints[0])
    assert np.allclose(rc._x, 0) and rc._y > 0
    rc.derive_speeds(waypoints[0])
    print(rc.waypoints)
    assert rc._x < 0 and np.allclose(rc._y, 0)
    rc.derive_speeds(waypoints[0])
    assert np.allclose(rc._x, 0) and rc._y < 0
    # continue straight with turning, to last waypoint
    rc.derive_speeds(waypoints[0])
    assert np.allclose(rc._x, 0) and rc._y < 0 and rc._w > 0

def test_append_urgent_destination():
    rc = RobotCommands()
    angle = math.pi / 2 # makes robot perspective same as field - easier
    og_position = np.array([0, 0, angle])
    gx = 1000
    rc.append_urgent_destination(np.array([gx, 0, None]), og_position)
    # check for max speed no matter how close
    for x in range(0, gx - 100):
        mock_position = np.array([x, 0, angle])
        rc.derive_speeds(mock_position)
        assert rc._x == rc.ROBOT_MAX_SPEED
    # extra test for speed limit
    low_speed_limit = 100
    rc.set_speed_limit(low_speed_limit)
    rc.derive_speeds(mock_position)
    assert rc._x == low_speed_limit
    
def test_set_waypoints():
    rc = RobotCommands()
    angle = math.pi / 2 # makes robot perspective same as field - easier
    og_pos = np.array([0, 0, angle])
    waypoints = [
        np.array([1000, 0, 0]),
        np.array([1000, 1000, 0]),
        np.array([0, 1000, 0]),
        np.array([0, 0, 0]),
    ]
    rc.set_waypoints(waypoints, og_pos)
    for i in range(len(waypoints)):
        assert (rc.waypoints[i] == waypoints[i]).all()

def test_predict_pos():
    rc = RobotCommands()
    angle = math.pi / 2 # makes robot perspective same as field - easier
    rc.set_speeds(100, 100, 1)
    og_pos = np.array([0, 0, angle])
    # this is usually used for small time intervals
    new_pos = rc.predict_pos(og_pos, .01)
    assert np.allclose(new_pos, np.array([1, 1, angle + .01]))

