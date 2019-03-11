"""Test game controller input. We're using the Logitech game controller. The
mapping is

LeftStick: Down=ABS_Y Right=ABS_X
RightStick: Right=ABS_Z Down=ABS_RZ
The ev_type is "Absolute"

"""
import inputs
from inputs import devices
from inputs import get_gamepad 

def main():
    print("Detected devices:")
    for device in devices:
        print(device)
    
    while True:
        events = get_gamepad()
        for event in events:
            if event.ev_type == 'Absolute':
                # Joystick input
                print(event.ev_type, event.code, event.state)



if __name__ == '__main__':
    main()


