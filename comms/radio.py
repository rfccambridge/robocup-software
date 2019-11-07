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

class Radio(object):
    # current xbee only can send once every ~50ms, sending faster may block
    MESSAGE_DELAY = .05
    
    def __init__(self, port=DEFAULT_PORT, baud_rate=DEFAULT_BAUD_RATE):
        # Find our XBee device connected to this computer
        self.device = XBeeDevice(port, baud_rate)

        # TODO: sometimes it errors about operating mode, try replugging xbee
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

    def send(self, message):
        for remote_device in self.net_devs:
            try:
                start = time.time()
                # asynchronous send is fast for first msg, but waits if too many 
                # long messages (>30?) take longer because they must be split
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

