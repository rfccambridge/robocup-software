import sys
import math
import time
import numpy as np
import pygame
# import gamestate file to use field dimension constants
# (as opposed to importing the class GameState)
sys.path.append('..')
from gamestate import gamestate as gs

# rendering constants
FIELD_LINE_WIDTH = 3
FIELD_COLOR = (0, 255, 0)
LINE_COLOR = (255, 255, 255)
GOAL_COLOR = (0, 0, 0)

ROBOT_LOST_COLOR = (200, 200, 200)
BLUE_TEAM_COLOR = (0, 0, 255)
YELLOW_TEAM_COLOR = (255, 255, 0)

BALL_COLOR = (255, 125, 0)

TRAJECTORY_COLOR = (255, 0, 0)

# Scale for the display window, or else it gets too large... (pixels/mm)
SCALE = 0.15
# how much space above the field for UI
UI_BUFFER_PX = 50
BUTTON_OFFSET_X = 5
BUTTON_OFFSET_Y = 10
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 40
BUTTON_COLOR = (0, 0, 100)
BUTTON_TEXT_COLOR = (255, 255, 255)

# how much space to include outside the field
WINDOW_BUFFER_PX = 20
TOTAL_SCREEN_WIDTH = int(gs.FIELD_X_LENGTH * SCALE) + WINDOW_BUFFER_PX * 2
TOTAL_SCREEN_HEIGHT = \
    int(gs.FIELD_Y_LENGTH * SCALE) + WINDOW_BUFFER_PX * 2 + UI_BUFFER_PX


class Visualizer(object):
    """Robocup homegrown visualization library that essentially does the same
    as the modules in OpenAI gym."""

    def __init__(self, gamestate, home_strategy, away_strategy):
        self._viewer = None
        self._clock = None

        self.user_click = None

        self._gamestate = gamestate
        # get references to strategy objects to display strategic information
        self._home_strategy = home_strategy
        self._away_strategy = away_strategy
        self._updating = True

        # Buttons for different commands (label : pygame.Rect)
        def generate_button_rect(n):
            return pygame.Rect(
                WINDOW_BUFFER_PX + (BUTTON_OFFSET_X + BUTTON_WIDTH) * n,
                BUTTON_OFFSET_Y,
                BUTTON_WIDTH,
                BUTTON_HEIGHT
            )
        self.buttons = {
            "timeout": generate_button_rect(0),
            "ref": generate_button_rect(1),
            "normal": generate_button_rect(2),
        }

        # Designed to be run in main thread so it works on more platforms
        pygame.init()
        self._viewer = pygame.display.set_mode(
            (TOTAL_SCREEN_WIDTH, TOTAL_SCREEN_HEIGHT)
        )
        pygame.display.set_caption("Robocup Visualizer")
        self._clock = pygame.time.Clock()

    # map ssl-vision field position to pixel x,y on viewer
    def field_to_screen(self, pos):
        assert(len(pos) == 2 and type(pos) == np.ndarray)
        pos = pos.copy().astype(float)
        # shift position so (0, 0) is the center of the field, as in ssl-vision
        pos += np.array([gs.FIELD_X_LENGTH / 2, gs.FIELD_Y_LENGTH / 2])
        # scale for display
        pos *= SCALE
        pos = pos.astype(int)
        # account for buffer space outside of field
        pos += WINDOW_BUFFER_PX
        # y becomes axis inverted in pygame (top left screen is 0,0)
        pos[1] = TOTAL_SCREEN_HEIGHT - pos[1]
        return pos

    # map screen pixels to field position
    def screen_to_field(self, pos):
        assert(len(pos) == 2 and type(pos) == np.ndarray)
        pos = pos.copy().astype(float)
        # revert y axis
        pos[1] = TOTAL_SCREEN_HEIGHT - pos[1]
        # account for buffer space outside of field
        pos -= WINDOW_BUFFER_PX
        # unscale display
        pos /= SCALE
        # shift position so that center becomes (0, 0)
        pos -= np.array([gs.FIELD_X_LENGTH / 2, gs.FIELD_Y_LENGTH / 2])
        return pos

    # map vector in ssl-vision coordinates (mm) to vector in x,y viewer pixels
    def scale_vector(self, vector):
        vector = vector.copy().astype(float)
        assert(len(vector) == 2 and type(vector) == np.ndarray)
        # scale for display
        vector *= SCALE
        # y becomes axis inverted in pygame (top left screen is 0,0)
        vector[1] *= -1
        return vector

    def visualization_loop(self):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()
        while self._updating:
            # make sure prints from all threads get flushed to terminal
            sys.stdout.flush()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._updating = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.user_click = np.array(pygame.mouse.get_pos())
                    self._gamestate.user_click_field = \
                        self.screen_to_field(self.user_click)
                    # print(self._gamestate.is_pos_valid(
                    #     self._gamestate.user_click_field, 'blue', 1
                    # ))
                    for label, rect in self.buttons.items():
                        if rect.collidepoint(self.user_click):
                            # prints current location of mouse
                            print('button pressed: ' + label)
            self._viewer.fill(FIELD_COLOR)
            self.render()
            pygame.display.flip()
            # yield to other threads - loop at most 20 times per second
            # is this the same as pygame.clock.tick()?
            time.sleep(.05)
        print("Exiting Pygame")
        pygame.quit()

    def render(self):
        assert(self._viewer is not None)
        # Draw Field
        # Boundary Lines
        hw, hh = gs.FIELD_X_LENGTH / 2, gs.FIELD_Y_LENGTH / 2
        top_left = self.field_to_screen(np.array([-hw, hh]))
        dims = (gs.FIELD_X_LENGTH * SCALE, gs.FIELD_Y_LENGTH * SCALE)
        boundary_lines_rect = [*top_left, *dims]
        pygame.draw.rect(self._viewer, LINE_COLOR, boundary_lines_rect, FIELD_LINE_WIDTH)
        pygame.draw.line(
            self._viewer,
            LINE_COLOR,
            self.field_to_screen(np.array([0, hh])),
            self.field_to_screen(np.array([0, -hh])),
            FIELD_LINE_WIDTH
        )
        # Center Circle
        pygame.draw.circle(
            self._viewer,
            LINE_COLOR,
            self.field_to_screen(np.array([0, 0])),
            int(gs.CENTER_CIRCLE_RADIUS * SCALE),
            FIELD_LINE_WIDTH
        )
        # Goals + Defence areas
        for team in ['blue', 'yellow']:
            top_left = self._gamestate.defense_area_corner(team) + \
                np.array([0, gs.DEFENSE_AREA_Y_LENGTH])
            dims = np.array([
                gs.DEFENSE_AREA_X_LENGTH * SCALE,
                gs.DEFENSE_AREA_Y_LENGTH * SCALE
            ])
            defense_area_rect = [
                *self.field_to_screen(top_left),
                *dims
            ]
            # defense_area_rect = list(map(tuple, defense_area_rect))
            pygame.draw.rect(self._viewer, LINE_COLOR, defense_area_rect, FIELD_LINE_WIDTH)
            goalposts = self._gamestate.get_defense_goal(team)
            pygame.draw.line(
                self._viewer,
                GOAL_COLOR,
                self.field_to_screen(goalposts[0]),
                self.field_to_screen(goalposts[1]),
                FIELD_LINE_WIDTH * 2
            )

        # Draw all the robots
        for (team, robot_id), pos in self._gamestate.get_all_robot_positions():
            pos = self._gamestate.get_robot_position(team, robot_id)
            robot_color = BLUE_TEAM_COLOR if team == 'blue' else YELLOW_TEAM_COLOR
            if self._gamestate.is_robot_lost(team, robot_id):
                robot_color = ROBOT_LOST_COLOR
            (x, y, w) = pos
            pygame.draw.circle(
                self._viewer,
                robot_color,
                self.field_to_screen(pos[:2]),
                int(gs.ROBOT_RADIUS * SCALE)
            )
            # indicate direction of robot
            arrow_scale = int(gs.ROBOT_RADIUS * SCALE) * 5
            pygame.draw.line(
                self._viewer,
                (255, 0, 0),
                self.field_to_screen(pos[:2]),
                self.field_to_screen(np.array([
                    x + math.cos(w) * arrow_scale,
                    y + math.sin(w) * arrow_scale
                ])),
                2
            )
            # draw waypoints for this robot
            robot_commands = self._gamestate.get_robot_commands(team, robot_id)
            prev_waypoint = pos
            for waypoint, min_speed, max_speed in robot_commands.waypoints:
                pygame.draw.line(
                    self._viewer,
                    (255, 0, 0),
                    self.field_to_screen(prev_waypoint[:2]),
                    self.field_to_screen(waypoint[:2]),
                    1
                )
                prev_waypoint = waypoint

        # Draw ball
        ball_screen_pos = self.field_to_screen(self._gamestate.get_ball_position())
        if not self._gamestate.is_ball_lost():
            pygame.draw.circle(
                self._viewer,
                BALL_COLOR,
                ball_screen_pos,
                int(gs.BALL_RADIUS * SCALE)
            )
            # draw ball velocity
            ball_screen_velocity = self.scale_vector(
                self._gamestate.get_ball_velocity()
            )
            pygame.draw.line(
                self._viewer,
                TRAJECTORY_COLOR,
                ball_screen_pos,
                ball_screen_pos + ball_screen_velocity,
                1
            )
            # draw where we think ball will be in 1s
            pygame.draw.circle(
                self._viewer,
                (0, 0, 0),
                self.field_to_screen(self._gamestate.predict_ball_pos(1)),
                int(gs.BALL_RADIUS * SCALE)
            )

        # draw user click location with a red 'X'
        if self.user_click is not None:
            self.draw_X(self.user_click, (255, 0, 0), 5, 2)

        # Draw buttons :)
        for label, rect in self.buttons.items():
            # TODO: produces false/misleading font errors when other things break
            pygame.draw.rect(self._viewer, BUTTON_COLOR, rect)
            myfont = pygame.font.SysFont('Arial', 30)
            textsurface = myfont.render(label, False, BUTTON_TEXT_COLOR)
            self._viewer.blit(textsurface, rect)

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
