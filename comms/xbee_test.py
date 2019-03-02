# If you are getting the error
# Could not open port "/dev/USBXXX", permission denied
# then make sure that your user has usb port access without sudo
# you can do this by adding user into dialout group. Google this.

"""
802.15.4 devices

    Click Load default firmware settings in the Radio Configuration toolbar to load the default values for the device firmware.
    Make sure API mode (API1 or API2) is enabled. To do so, set the AP parameter value to 1 (API mode without escapes) or 2 (API mode with escapes).
    Configure ID (PAN ID) setting to CAFE.
    Configure CH (Channel setting) to C.
    Click Write radio settings in the Radio Configuration toolbar to apply the new values to the module.
    Once you have configured both modules, check to make sure they can see each other. Click Discover radio modules in the same network, the second button of the device panel in the Radio Modules view. The other device must be listed in the Discovering remote devices dialog.
"""
from digi.xbee.devices import XBeeDevice
import time

PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600

DATA_TO_SEND = '-1,50,0,0\r\n'


def main():
    print(" +--------------------------------------+")
    print(" | XBee Python Library Send Data Sample |")
    print(" +--------------------------------------+\n")

    device = XBeeDevice(PORT, BAUD_RATE)

    try:
        device.open()

        # Obtain the remote XBee device from the XBee network.
        xbee_network = device.get_network()

        # Try to find devices
        xbee_network.start_discovery_process()
        time.sleep(3)  # wait 5 seconds
        xbee_network.stop_discovery_process()
        found_devs = xbee_network.get_devices()
        if not found_devs:
            print("Cound not find any devices")
            exit(1)
        else:
            print("Found %d other devices" % len(found_devs))
        
        for remote_device in found_devs:
            print("Sending data to %s >> %s..." % (remote_device.get_64bit_addr(), DATA_TO_SEND))
            for _ in range(10):
                device.send_data(remote_device, DATA_TO_SEND)

    finally:
        if device is not None and device.is_open():
            device.close()


if __name__ == '__main__':
    main()
    
