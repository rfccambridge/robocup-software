"""Test game controller input. We're using the Logitech game controller. The
mapping is

LeftStick: Down=ABS_Y Right=ABS_X
RightStick: Right=ABS_Z Down=ABS_RZ
The ev_type is "Absolute"

"""
import pygame

def main():
    pygame.joystick.init()
    pygame.display.init()
    pygame.joystick.Joystick(0).init()

    print('Name of Joystick:')
    js = pygame.joystick.Joystick(0)
    print(js.get_name())

    while True:
        pygame.event.pump()
        a = js.get_axis(0)
        b = js.get_axis(1)
        c = js.get_axis(2)
        d = js.get_axis(3)
        print("Axis 0 1 2 3: {} {} {} {}".format(a, b, c, d))


if __name__ == '__main__':
    main()


