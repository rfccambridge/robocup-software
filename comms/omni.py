"""XBee communications class for omniwheel robocup devices. Read the following for setting up
the XBee device we are using and common troubleshooting errors.

802.15.4 devices
    Click Load default firmware settings in the Radio Configuration toolbar to load the default values for the device firmware.
    Make sure API mode (API1 or API2) is enabled. To do so, set the AP parameter value to 1 (API mode without escapes) or 2 (API mode with escapes).
    Configure ID (PAN ID) setting to CAFE.
    Configure CH (Channel setting) to C.
    Click Write radio settings in the Radio Configuration toolbar to apply the new values to the module.
    Once you have configured both modules, check to make sure they can see each other. Click Discover radio modules in the same network, the second button of the device panel in the Radio Modules view. The other device must be listed in the Discovering remote devices dialog.

Troubleshooting:
    If you are getting the error
    Could not open port "/dev/USBXXX", permission denied
    then make sure that your user has usb port access without sudo
    you can do this by adding user into dialout group. Google this.
"""
from digi.xbee.devices import XBeeDevice
from digi.xbee.exception import XBeeException
import time

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD_RATE = 9600
MAGIC_KEY = "42069,"  # Key to ensure that xbee message is not corrupted.
                     # Match with firmware, should be put at start of message

class OmniComms(object):

    def __init__(self, port=DEFAULT_PORT, baud_rate=DEFAULT_BAUD_RATE):
        # Find our XBee device connected to this computer
        self.device = XBeeDevice(port, baud_rate)

        self.device.open()

        # Obtain the remote XBee devices from the XBee network.
        xbee_network = self.device.get_network()

        # Try to find devices
        xbee_network.start_discovery_process()
        time.sleep(3)  # wait a few seconds to find all of the xbees
        xbee_network.stop_discovery_process()
        self.net_devs = xbee_network.get_devices()
        if not self.net_devs:
            raise RuntimeError("Cound not find any XBEE devices on network")

    def send(self, command):
        for remote_device in self.net_devs:
            try:
                start = time.time()
                # message length of 27 was .0001 ms send time, quickly increases when longer
                # we suspect xbee is crappy at splitting up messages
                # also time spikes when too many messages are sent? can we get beter xbee?
                message = MAGIC_KEY + command + '\n'
                self.device.send_data_async(remote_device, message)
                delta = time.time() - start
                if delta > .001:
                    print("xbee send is taking a long time, message too long or rate too fast?")
                    print("time taken: " + str(delta))
                    print("message length: " + str(len(message)))
            except XBeeException as xbee_exp:
                print(str(xbee_exp))


    def read(self):
        for remote_device in self.net_devs:
            try:
                return self.device.read_data()
            except XBeeException as xbee_exp:
                print(str(xbee_exp))

    def close(self):
        if self.device.is_open():
            self.device.close()


if __name__ == '__main__':
    test = OmniComms()
    for _ in range(5):
        test.send('-1,50,50,0,500')  # go diagonally for 500 ms
        test.send('-1,-50,50,0,500')  # go diagonally for 500 ms
        test.send('-1,-50,-50,0,500')  # go diagonally for 500 ms
        test.send('-1,50,-50,0,500')  # go diagonally for 500 ms

