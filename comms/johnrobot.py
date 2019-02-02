from omni import OmniComms
import numpy as np
import time
import threading


class JohnRobot(object):
    """Class that controls John's old robot he made in high school. Essentially
    the same as robocup except larger, slightly different wheels, and different
    arduino used to control. Commands should still be in the same format"""

    def __init__(self):
        self.comms = OmniComms()

    def move(self, forward, lateral, w):
        """Move forward, laterally, and rotation. Should be given as a int
        from 0 to 255, with 255 being the fastest."""
        # Use -1 as first element to broadcast to all robots
        robot_id = -1
        f = int(np.clip(forward, -255, 255))
        l = int(np.clip(lateral, -255, 255))
        w = int(np.clip(w, -255, 255))
        cmd = "{},{},{},{}".format(robot_id, l, f, w)
        self.comms.send(cmd)

    def move_time(self, forward, lateral, w, dt):
        def _move_loop():
            start = time.time()
            while True:
                if time.time() - start > dt:
                    break
                self.move(forward, lateral, w)
        b = threading.Thread(name='background', target=_move_loop)
        b.start()


