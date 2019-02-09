import numpy as np

class RealWorldCoordTransformer(object):

    def __init__(self):
        pass

    def transform(self, w_robot, dest):
        """Transforms real world vector and transforms it into a normalized vector in the
        reference frame of the robot"""
        if dest == (0, 0):
            return dest
        x_dest, y_dest = dest
        w_rot = np.arctan2(x_dest, y_dest) + w_robot - np.pi / 2
        return (np.cos(w_rot), -np.sin(w_rot))
        # x_dest, y_dest = dest
        # o_angle = np.arctan2(y_dest, x_dest)
        # new_angle = w_robot - o_angle
        # if new_angle > np.pi:
        #     new_angle -= 2 * np.pi
        # elif new_angle < -np.pi:
        #     new_angle += 2 * np.pi
        
        # x, y = np.sin(new_angle), np.cos(new_angle)
        # return x, y

    def magnitude(self, v):
        x, y = v
        return (x**2 + y**2) ** .5


if __name__=="__main__":
    # Test 1
    a = RealWorldCoordTransformer()
    # assert(a.transform(np.pi / 2, (1, 1)), )
    # Test 2
    print(a.transform(np.pi / 3, (200 * np.cos(np.pi / 6), 200 * np.sin(np.pi / 6)))) # (0.8660254037844386, 0.5)
    print(a.transform(-np.pi / 2, (-200 * np.cos(np.pi / 6), 200 * np.sin(np.pi / 6)))) # (-0.4999999999999996, 0.8660254037844388)



