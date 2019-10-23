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

ROBOT_SIZE = 90 # mm
ROBOT_COLOR = (0, 0, 0)
ROBOT_LOST_COLOR = (200, 200, 200)

BALL_SIZE = 21 # mm
BALL_COLOR = (255, 125, 0)

WAYPOINT_SIZE = 3
WAYPOINT_COLOR = (0, 0, 0)

VECTOR_SCALE = 10 # px / (mm/s) ?
TRAJECTORY_COLOR = (255, 0, 0)

# Scale for the display window, or else it gets too large... (pixels/mm)
SCALE = 0.15
# how much space above the field for UI
UI_BUFFER_PX = 50
BUTTON_OFFSET_X = 5
BUTTON_OFFSET_Y = 5
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 40

# how much space to include outside the field
WINDOW_BUFFER_PX = 20
TOTAL_SCREEN_WIDTH = int(FIELD_W * SCALE) + WINDOW_BUFFER_PX * 2
TOTAL_SCREEN_HEIGHT = int(FIELD_H * SCALE) + WINDOW_BUFFER_PX * 2 + UI_BUFFER_PX

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

        # Buttons for different commands (label : pygame.Rect)
        def generate_button_rect(n):
            return pygame.Rect(
                WINDOW_BUFFER_PX + BUTTON_OFFSET_X * n + BUTTON_WIDTH * (n - 1),
                BUTTON_OFFSET_Y,
                BUTTON_WIDTH,
                BUTTON_HEIGHT
            )
        self.buttons = {
            "timeout" : generate_button_rect(0),
            "ref" : generate_button_rect(1),
            "normal" : generate_button_rect(2),
        }

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
        pos = (pos[0] - WINDOW_BUFFER_PX, pos[1] - WINDOW_BUFFER_PX - UI_BUFFER_PX)
        # unscale display
        pos = (int(pos[0] / SCALE), int(pos[1] / SCALE))
        # shift position so that center becomes (0, 0)
        pos = (pos[0] - FIELD_W / 2, pos[1] - FIELD_H / 2)
        return pos

    # map vector in ssl-vision coordinates to vector in x,y viewer pixels
    def scale_vector(self, vector):
        assert(len(vector) == 2 and type(vector) == tuple)
        # scale for display
        vector = (int(vector[0] * VECTOR_SCALE), int(vector[1] * VECTOR_SCALE))
        # y becomes axis inverted in pygame (top left screen is 0,0)
        vector = (vector[0], -vector[1])
        return vector    

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
                    for label, rect in self.buttons.items():
                        if rect.collidepoint(mouse_pos):
                            # prints current location of mouse
                            print('button pressed: ' + label)
            start_time = time.time()
            self._viewer.fill(FIELD_COLOR)
            self.render()
            pygame.display.flip()
            # yield to other threads - run this loop at most 20 times per second
            # is this the same as pygame.clock.tick()?
            time.sleep(.05)

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

        # Draw all the robots
        for robot_id in self._gamestate.get_blue_team_robot_ids():
            pos = self._gamestate.get_robot_position(robot_id)
            robot_color = ROBOT_COLOR
            if self._gamestate.is_robot_lost(robot_id):
                robot_color = ROBOT_LOST_COLOR
            (x, y, w) = pos
            pygame.draw.circle(
                self._viewer,
                robot_color,
                self.scale_pos((x, y)),
                int(ROBOT_SIZE * SCALE)
            )
            # indicate direction of robot
            arrow_scale = int(ROBOT_SIZE * SCALE) * 5
            pygame.draw.line(
                self._viewer,
                (255, 0, 0),
                self.scale_pos((x, y)),
                self.scale_pos((x + math.cos(w) * arrow_scale, y + math.sin(w) * arrow_scale)),
                2
            )

            # TODO: draw commands + analyzed trajectories for this robot


        # Draw ball
        if not self._gamestate.is_ball_lost():
            x, y = self.scale_pos(self._gamestate.get_ball_position())
            pygame.draw.circle(
                self._viewer,
                BALL_COLOR,
                (x, y),
                int(BALL_SIZE * SCALE)
            )
            # draw ball trajectory
            dx, dy = self._gamestate.get_ball_velocity()
            pygame.draw.line(
                self._viewer,
                TRAJECTORY_COLOR,
                (x, y),
                (x + dx*SCALE, y + dy*SCALE),
                1
            )
            

        # draw user click location with a red 'X'
        if self.user_click:
            self.draw_X(self.user_click, (255, 0, 0), 5, 2)

        # Draw buttons :)
        for label, rect in self.buttons.items():
            #myfont = pygame.font.SysFont('Comic Sans MS', 30)
            #textsurface = myfont.render(label, False, (0, 0, 0))
            #self._viewer.blit(textsurface)
            pygame.draw
            pygame.draw.rect(self._viewer, [0, 0, 100, 0.1], rect)
        

    def close(self):
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None

    # drawing helper functions
    def draw_X(self, pos, color, size, width):
        top_left = (pos[0] - size, pos[1] - size)
        bottom_right = (pos[0] + size, pos[1] + size)
        top_right = (pos[0] + size, pos[1] - size)
        bottom_left = (pos[0] - size, pos[1] + size)
        pygame.draw.line(self._viewer, color, top_left, bottom_right, width)
        pygame.draw.line(self._viewer, color, bottom_left, top_right, width)



