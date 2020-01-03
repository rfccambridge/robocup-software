import sys
import math
import time
import numpy as np
import pygame
# import gamestate file to use field dimension constants
# (as opposed to importing the class GameState)
sys.path.append('..')
from gamestate import gamestate as gs

# rendering constants (dimensions are in field - mm)
FIELD_LINE_WIDTH = 20
FIELD_COLOR = (0, 255, 0)
LINE_COLOR = (255, 255, 255)
GOAL_COLOR = (0, 0, 0)

ROBOT_LOST_COLOR = (200, 200, 200)
ROBOT_FRONT_COLOR = (255, 0, 0)
ROBOT_FRONT_LINE_WIDTH = 15
SELECTION_COLOR = (255, 0, 255)
SELECTION_WIDTH = 10
BLUE_TEAM_COLOR = (0, 0, 255)
YELLOW_TEAM_COLOR = (255, 255, 0)

BALL_COLOR = (255, 125, 0)

TRAJECTORY_COLOR = (255, 0, 0)
TRAJECTORY_LINE_WIDTH = 10
WAYPOINT_RADIUS = 25


# Scale for the display window, or else it gets too large... (pixels/mm)
SCALE = 0.15  # below .1 messes stuff up

# EVERYTHING IS IN FIELD DIMENSIONS!!! (real world mm, 0,0 is center)
UI_BUFFER = 300  # how much space above the field for UI
BUTTON_OFFSET_X = 30
BUTTON_OFFSET_Y = 60
BUTTON_WIDTH = 600
BUTTON_HEIGHT = 240
BUTTON_COLOR = (0, 0, 100)
BUTTON_TEXT_COLOR = (255, 255, 255)

# how much space to include outside the field
WINDOW_BUFFER = 70
TOTAL_SCREEN_WIDTH = int((gs.FIELD_X_LENGTH + 2 * WINDOW_BUFFER) * SCALE)
TOTAL_SCREEN_HEIGHT = \
    int((gs.FIELD_Y_LENGTH + 2 * WINDOW_BUFFER + UI_BUFFER) * SCALE)


class Visualizer(object):
    """Robocup homegrown visualization library that essentially does the same
    as the modules in OpenAI gym."""

    def __init__(self, gamestate, home_strategy, away_strategy):
        self._viewer = None
        self._clock = None

        self.user_click_down = None
        self.user_click_up = None

        self._gamestate = gamestate
        # get references to strategy objects to display strategic information
        self._home_strategy = home_strategy
        self._away_strategy = away_strategy
        self._updating = True

        # Buttons for different commands (label : pygame.Rect)
        def button_pos(n):
            return (
                gs.FIELD_MIN_X + (BUTTON_OFFSET_X + BUTTON_WIDTH) * n,
                gs.FIELD_MAX_Y + UI_BUFFER + BUTTON_OFFSET_Y,
            )
        self.buttons = {
            "timeout": button_pos(0),
            "ref": button_pos(1),
            "normal": button_pos(2),
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
        if len(pos) == 3:
            # only consider x, y of robot positions
            pos = pos[:2]
        pos = np.array(pos).astype(float)
        # shift position so (0, 0) is the center of the field, as in ssl-vision
        pos += np.array([gs.FIELD_MAX_X, gs.FIELD_MAX_Y])
        # account for buffer space outside of field
        pos += WINDOW_BUFFER
        # scale for display
        pos *= SCALE
        pos = pos.astype(int)
        # y becomes axis inverted in pygame (top left screen is 0,0)
        pos[1] = TOTAL_SCREEN_HEIGHT - pos[1]
        return pos

    # map screen pixels to field position
    def screen_to_field(self, pos):
        pos = np.array(pos).astype(float)
        # revert y axis
        pos[1] = TOTAL_SCREEN_HEIGHT - pos[1]
        # unscale display
        pos /= SCALE
        # account for buffer space outside of field
        pos -= WINDOW_BUFFER
        # shift position so that center becomes (0, 0)
        pos -= np.array([gs.FIELD_MAX_X, gs.FIELD_MAX_Y])
        return pos

    # designed to run in main thread, for pygame to work on all platforms
    def visualization_loop(self, loop_sleep):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()
        while self._updating:
            # make sure prints from all threads get flushed to terminal
            sys.stdout.flush()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._updating = False
                if event.type == pygame.KEYDOWN:
                    # hotkey controls
                    if event.key == pygame.K_b:
                        self.select_ball()
                    # toggle dribbler
                    if event.key == pygame.K_d:
                        old = self._gamestate.user_dribble_command
                        self._gamestate.user_dribble_command = not old
                    # charge while key down
                    if event.key == pygame.K_c:
                        self._gamestate.user_charge_command = True
                    # kick only once
                    if event.key == pygame.K_k:
                        self._gamestate.user_kick_command = True
                    else:
                        self._gamestate.user_kick_command = False
                if event.type == pygame.KEYUP:
                    # stop charging on release
                    if event.key == pygame.K_c:
                        self._gamestate.user_charge_command = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.user_click_up = None
                    self.user_click_down = self.screen_to_field(
                        pygame.mouse.get_pos()
                    )

                    # trigger button clicks
                    for label, pos in self.buttons.items():
                        dims = (BUTTON_WIDTH, BUTTON_HEIGHT)
                        if self.is_collision(pos, dims, pygame.mouse.get_pos()):
                            # prints current location of mouse
                            print('button pressed: ' + label)

                    # FOR DEBUGGING:
                    # print(self._gamestate.is_pos_valid(
                    #     self.user_click_down, 'blue', 1
                    # ))

                if event.type == pygame.MOUSEBUTTONUP:
                    self.user_click_up = self.screen_to_field(
                        pygame.mouse.get_pos()
                    )
                    # ball/robot selection
                    down, up = self.user_click_down, self.user_click_up
                    robot_clicked = \
                        self._gamestate.robot_at_position(down) and \
                        self._gamestate.robot_at_position(up)
                    ball_clicked = \
                        self._gamestate.ball_overlap(down).any() and \
                        self._gamestate.ball_overlap(up).any()
                    if robot_clicked or ball_clicked:
                        self.user_click_down = None
                        self._gamestate.user_click_position = None
                        self._gamestate.user_drag_vector = None
                        if ball_clicked:
                            self.select_ball()
                        elif robot_clicked:
                            self.select_robot(robot_clicked)

                    if self.user_click_down is not None:
                        # store xy of original mouse down, and drag vector
                        self._gamestate.user_click_position = \
                            self.user_click_down
                        self._gamestate.user_drag_vector = \
                            self.user_click_up - self.user_click_down

            self._viewer.fill(FIELD_COLOR)
            self.render()
            pygame.display.flip()
            # yield to other threads
            time.sleep(loop_sleep)
        print("Exiting Pygame")
        pygame.quit()

    def select_ball(self):
        self._gamestate.user_selected_ball = True
        self._gamestate.user_selected_robot = None

    def select_robot(self, robot):
        self._gamestate.user_selected_robot = robot
        self._gamestate.user_selected_ball = False

    def render(self):
        assert(self._viewer is not None)
        # Draw Field
        # Boundary Lines
        top_left = (gs.FIELD_MIN_X, gs.FIELD_MAX_Y)
        dims = (gs.FIELD_X_LENGTH, gs.FIELD_Y_LENGTH)
        self.draw_rect(LINE_COLOR, top_left, dims, FIELD_LINE_WIDTH)
        # Mid line
        top_mid = (0, gs.FIELD_MAX_Y)
        bottom_mid = (0, gs.FIELD_MIN_Y)
        self.draw_line(LINE_COLOR, top_mid, bottom_mid, FIELD_LINE_WIDTH)
        # Center Circle
        self.draw_circle(
            LINE_COLOR,
            (0, 0),
            gs.CENTER_CIRCLE_RADIUS,
            FIELD_LINE_WIDTH
        )
        # Goals + Defence areas
        for team in ['blue', 'yellow']:
            top_left = self._gamestate.defense_area_corner(team) + \
                (0, gs.DEFENSE_AREA_Y_LENGTH)
            dims = (gs.DEFENSE_AREA_X_LENGTH, gs.DEFENSE_AREA_Y_LENGTH)
            self.draw_rect(LINE_COLOR, top_left, dims, FIELD_LINE_WIDTH)
            goalposts = self._gamestate.get_defense_goal(team)
            self.draw_line(GOAL_COLOR, *goalposts, FIELD_LINE_WIDTH * 2)

        # Draw all the robots
        for (team, robot_id), pos in self._gamestate.get_all_robot_positions():
            pos = self._gamestate.get_robot_position(team, robot_id)
            robot_color = BLUE_TEAM_COLOR if team == 'blue' else YELLOW_TEAM_COLOR
            if self._gamestate.is_robot_lost(team, robot_id):
                robot_color = ROBOT_LOST_COLOR
            (x, y, w) = pos
            self.draw_circle(robot_color, pos, gs.ROBOT_RADIUS)
            # draw id of robot
            self.draw_text(str(robot_id), pos, 100, (0, 0, 0), 'Arial')
            # indicate front of robot
            draw_radius = gs.ROBOT_RADIUS - ROBOT_FRONT_LINE_WIDTH / 2
            corner1 = np.array([
                draw_radius * np.cos(w + gs.ROBOT_FRONT_ANGLE),
                draw_radius * np.sin(w + gs.ROBOT_FRONT_ANGLE),
            ]) + pos[:2]
            corner2 = np.array([
                draw_radius * np.cos(w - gs.ROBOT_FRONT_ANGLE),
                draw_radius * np.sin(w - gs.ROBOT_FRONT_ANGLE),
            ]) + pos[:2]
            self.draw_line(ROBOT_FRONT_COLOR, corner1, corner2, ROBOT_FRONT_LINE_WIDTH)
            robot_commands = self._gamestate.get_robot_commands(team, robot_id)
            # draw charge level
            charge = robot_commands.charge_level / robot_commands.MAX_CHARGE_LEVEL
            charge_end = np.array([pos[0], pos[1] + charge * gs.ROBOT_RADIUS])
            self.draw_line((255, 255, 255), pos, charge_end, 15)
            # draw dribbler zone if on
            if robot_commands.is_dribbling:
                self.draw_circle(
                    TRAJECTORY_COLOR,
                    self._gamestate.dribbler_pos(team, robot_id),
                    20
                )
            # draw waypoints for this robot
            prev_waypoint = pos
            for waypoint in robot_commands.waypoints:
                self.draw_waypoint(waypoint)
                self.draw_line(
                    TRAJECTORY_COLOR,
                    prev_waypoint,
                    waypoint,
                    TRAJECTORY_LINE_WIDTH
                )
                prev_waypoint = waypoint
            # TEST: draw interception range
            interception_range = self._home_strategy.intercept_range(0)
            if interception_range is not None:
                self.draw_position(interception_range[0])
                midpoint = (interception_range[1]+interception_range[0])/2
                self.draw_position(midpoint)
                self.draw_position(interception_range[1])                
            # highlight selected robot
            if (team, robot_id) == self._gamestate.user_selected_robot:
                self.draw_circle(
                    SELECTION_COLOR,
                    pos,
                    gs.ROBOT_RADIUS + SELECTION_WIDTH,
                    SELECTION_WIDTH
                )

        # Draw ball
        ball_pos = self._gamestate.get_ball_position()
        if not self._gamestate.is_ball_lost():
            # draw where the best position is to kick towards the mouse.
            # mouse_pos = self.screen_to_field(pygame.mouse.get_pos())
            # kick_pos = self._home_strategy.best_kick_pos(ball_pos, mouse_pos)
            # self.draw_waypoint(kick_pos)

            # draw where we think ball will be in 1s
            predicted_pos = self._gamestate.predict_ball_pos(1)
            self.draw_circle((0, 0, 0), predicted_pos, gs.BALL_RADIUS)
            # draw actual ball
            self.draw_circle(BALL_COLOR, ball_pos, gs.BALL_RADIUS)
            # highlight ball if selected
            if self._gamestate.user_selected_ball:
                self.draw_circle(
                    SELECTION_COLOR,
                    ball_pos,
                    gs.BALL_RADIUS + SELECTION_WIDTH,
                    SELECTION_WIDTH
                )

            # draw ball velocity
            velocity = self._gamestate.get_ball_velocity()
            self.draw_line(
                TRAJECTORY_COLOR,
                ball_pos,
                ball_pos + velocity,
                TRAJECTORY_LINE_WIDTH
            )

        # debug best goalie pos
        self.draw_waypoint(self._home_strategy.best_goalie_pos())

        # draw user click location with a red 'X'
        if self.user_click_down is not None and self.user_click_up is None:
            self.draw_X(self.user_click_down, (255, 0, 0), 30, 15)
            # draw drag direction
            self.draw_line(
                TRAJECTORY_COLOR,
                self.user_click_down,
                self.screen_to_field(pygame.mouse.get_pos()),
                15
            )

        # Draw buttons :)
        for label, pos in self.buttons.items():
            # produces false/misleading font errors when other things break
            dims = (BUTTON_WIDTH, BUTTON_HEIGHT)
            self.draw_rect(BUTTON_COLOR, pos, dims)
            self.draw_text(label, pos, 180, BUTTON_TEXT_COLOR, 'Arial')

    def close(self):
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None

    # drawing helper functions (that take field position args)
    def draw_line(self, color, start, end, width):
        pygame.draw.line(
            self._viewer,
            color,
            self.field_to_screen(start),
            self.field_to_screen(end),
            int(width * SCALE)
        )

    def draw_circle(self, color, center, radius, width=None):
        if width is None:
            width = radius
        pygame.draw.circle(
            self._viewer,
            color,
            self.field_to_screen(center),
            int(radius * SCALE),
            int(width * SCALE)
        )

    def draw_rect(self, color, top_left, dims, width=0):
        dims = np.array(dims).astype(float) * SCALE
        pygame.draw.rect(
            self._viewer,
            color,
            [*self.field_to_screen(top_left), *dims],
            int(width * SCALE)
        )

    def is_collision(self, top_left, dims, pos):
        dims = np.array(dims).astype(float) * SCALE
        rect = pygame.Rect([*self.field_to_screen(top_left), *dims])
        return rect.collidepoint(pos)

    def draw_text(self, text, top_left, size, color, font):
        myfont = pygame.font.SysFont(font, int(size * SCALE))
        textsurface = myfont.render(text, False, color)
        self._viewer.blit(textsurface, self.field_to_screen(top_left))

    def draw_waypoint(self, pos):
        self.draw_circle(TRAJECTORY_COLOR, pos[:2], WAYPOINT_RADIUS)
        x, y, w = pos
        arrow = WAYPOINT_RADIUS * 2 * np.array([math.cos(w), math.sin(w)])
        end = np.array([x, y]) + arrow
        self.draw_line(TRAJECTORY_COLOR, pos, end, TRAJECTORY_LINE_WIDTH)

    def draw_position(self, pos):
        self.draw_circle(TRAJECTORY_COLOR, pos, WAYPOINT_RADIUS)

    def draw_X(self, pos, color, size, width):
        pos = np.array(pos).astype(float)
        top_left = pos - size
        bottom_right = pos + size
        top_right = (pos[0] + size, pos[1] - size)
        bottom_left = (pos[0] - size, pos[1] + size)
        self.draw_line(color, top_left, bottom_right, width)
        self.draw_line(color, bottom_left, top_right, width)
