import pyglet
import time

WINDOW_W = 400
WINDOW_H = 400

class Vis(object):
    """Robocup homegrown visualization library that essentially does the same
    as the modules in OpenAI gym."""
    
    def __init__(self):
        self.viewer = None

    def render(self, ssl_vision_packet):
        if self.viewer is None:
            from gym.envs.classic_control import rendering
            self.viewer = rendering.Viewer(WINDOW_W, WINDOW_H)
            # pole = rendering.FilledPolygon([(0,0), (100,0), (200,200), (0,150)])
            # pole.set_color(.8,.6,.4)
            # self.viewer.add_geom(pole)
            self.transform = rendering.Transform()
        
        # Render all of the robots as a circle with an arrow.
        # we expect SSL-vision to have the detections in the following format.
        # "detections": {
        #     "robots_yellow": [
        #     {
        #         "confidence": 0.930344820022583,
        #         "area": 78,
        #         "x": -14.979391098022461,
        #         "y": -12.432811737060547,
        #         "z": 0,
        #         "pixel_x": 276.5769348144531,
        #         "pixel_y": 225.73077392578125
        #     }
        #     "{... other yellow robots ...}"
        #     ],
        #     "robots_blue": [
        #     {
        #         "confidence": 0.930344820022583,
        #         "area": 78,
        #         "x": -14.979391098022461,
        #         "y": -12.432811737060547,
        #         "z": 0,
        #         "pixel_x": 276.5769348144531,
        #         "pixel_y": 225.73077392578125
        #     }
        #     "{... other blue robots ...}"
        #     ]
        # }
        try:
            yellow_robots = ssl_vision_packet["detection"]['robots_yellow']
        except:
            yellow_robots = []
        try:
            blue_robots = ssl_vision_packet["detection"]['robots_blue']
        except:
            blue_robots = []
    
        for robot in yellow_robots + blue_robots:
            x, y = robot["x"], robot["y"]
            pts = [(x + dx, y + dy) for dx in [-5, 5] for dy in [-5, 5]]
            robot = rendering.FilledPolygon(pts)
            robot.set_color(0.0, 0.7, 0.1)
    
        self.viewer.render()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

if __name__ == '__main__':
    a = Vis()
    for _ in range(100):
        a.render()
        time.sleep(0.2)