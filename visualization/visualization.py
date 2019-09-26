import math
import time
import numpy as np
import threading
import pygame

# The size of the field (should match location data from ssl-vision)
FIELD_W = 9000
FIELD_H = 6000
CENTER_CIRCLE_RADIUS = 495
FIELD_LINE_WIDTH = 3

# rendering constants
FIELD_COLOR = (0, 255, 0)
LINE_COLOR = (255, 255, 255)

ROBOT_SIZE = 12
ROBOT_COLOR = (0, 0, 0)

BALL_SIZE = 5
BALL_COLOR = (255, 125, 0)

WAYPOINT_SIZE = 3
WAYPOINT_COLOR = (0, 0, 0)

# Scale for the display window, or else it gets too large... (pixels/mm)
SCALE = 0.15
# how much space to include outside the field
WINDOW_BUFFER_PX = 20
TOTAL_SCREEN_WIDTH = int(FIELD_W * SCALE) + WINDOW_BUFFER_PX * 2
TOTAL_SCREEN_HEIGHT = int(FIELD_H * SCALE) + WINDOW_BUFFER_PX * 2

class Visualizer(object):
    """Robocup homegrown visualization library that essentially does the same
    as the modules in OpenAI gym."""
    
    def __init__(self, gamestate):
        self._viewer = None
        self._clock = None
        
        self.user_click = None
        self.user_click_field = None

        self._gamestate = gamestate

        self._updating = False
        self._visualization_thread = None

    # map ssl-vision field position to pixel x,y on viewer
    def scale_pos(self, pos):
        assert(len(pos) == 2 and type(pos) == tuple)
        # shift position so (0, 0) becomes the center of the field, as in ssl-vision
        pos = (pos[0] + FIELD_W / 2, pos[1] + FIELD_H / 2)
        # scale for display
        pos = (int(pos[0] * SCALE), int(pos[1] * SCALE))
        # account for buffer space outside of field
        pos = (pos[0] + WINDOW_BUFFER_PX, pos[1] + WINDOW_BUFFER_PX)
        # y becomes axis inverted in pygame (top left screen is 0,0)
        pos = (pos[0], TOTAL_SCREEN_HEIGHT - pos[1])
        return pos

    # map screen pixels to field position
    def unscale_pos(self, pos):
        assert(len(pos) == 2 and type(pos) == tuple)
        # revert y axis
        pos = (pos[0], TOTAL_SCREEN_HEIGHT - pos[1])
        # account for buffer space outside of field
        pos = (pos[0] - WINDOW_BUFFER_PX, pos[1] - WINDOW_BUFFER_PX)
        # unscale display
        pos = (int(pos[0] / SCALE), int(pos[1] / SCALE))
        # shift position so that center becomes (0, 0)
        pos = (pos[0] - FIELD_W / 2, pos[1] - FIELD_H / 2)
        return pos

    def start_visualizing(self):
        self._updating = True
        self._visualization_thread = threading.Thread(target=self.visualization_loop)
        self._visualization_thread.start()

    def visualization_loop(self):
        pygame.init()
        self._viewer = pygame.display.set_mode((TOTAL_SCREEN_WIDTH, TOTAL_SCREEN_HEIGHT))
        pygame.display.set_caption("Robocup Visualizer")
        self._clock = pygame.time.Clock()
        while self._updating:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._updating = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.user_click = pygame.mouse.get_pos()
                    self.user_click_field = self.unscale_pos(self.user_click)                    
            start_time = time.time()
            self._viewer.fill(FIELD_COLOR)
            self.render()
            pygame.display.flip()
            self._clock.tick(20)
        pygame.quit()        

    def stop_visualizing(self):
        self._updating = False
        self._visualization_thread.join()
        self._visualization_thread = None

    def render(self):
        assert(self._viewer is not None)
        # draw field landmarks
        pygame.draw.circle(
            self._viewer,
            LINE_COLOR,
            self.scale_pos((0,0)),
            int(CENTER_CIRCLE_RADIUS * SCALE),
            FIELD_LINE_WIDTH
        )
        hw, hh = FIELD_W / 2, FIELD_H / 2
        top_left = self.scale_pos((-hw, hh))
        dims = (FIELD_W * SCALE, FIELD_H * SCALE)
        boundary_lines_rect = [*top_left, *dims]
        pygame.draw.rect(self._viewer, LINE_COLOR, boundary_lines_rect, FIELD_LINE_WIDTH)
        pygame.draw.line(
            self._viewer,
            LINE_COLOR,
            self.scale_pos((0, hh)),
            self.scale_pos((0, -hh)),
            FIELD_LINE_WIDTH
        )

        # Draw ball
        pygame.draw.circle(
            self._viewer,
            BALL_COLOR,
            self.scale_pos(self._gamestate.ball),
            BALL_SIZE
        )

        # draw user click location
        if self.user_click:
            pygame.draw.circle(self._viewer, (0, 0, 0), self.user_click, 5)
            
        # Draw all the robots
        for robot_id, loc in self._gamestate.robots.items():
            (x, y, w) = loc
            pygame.draw.circle(
                self._viewer,
                ROBOT_COLOR,
                self.scale_pos((x, y)),
                ROBOT_SIZE
            )
            # indicate direction of robot
            arrow_scale = ROBOT_SIZE * 6
            pygame.draw.line(
                self._viewer,
                (255, 0, 0),
                self.scale_pos((x, y)),
                self.scale_pos((x + math.cos(w) * arrow_scale, y + math.sin(w) * arrow_scale)),
                1
            )

            # TODO: draw any trajectories for this robot
            if robot_id in self._gamestate.trajectories:
                pass
            
    def close(self):
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None

