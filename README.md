# Robocup Software
https://docs.google.com/document/d/1Eim1MRx77IE2ieGvYYDAL3BJYKYtR9JhJai6PuHB-iw/edit

__Python 3__ is required, due to compatibility issues with the pyserial module.
In some cases, you may have to use python and pip commands without the 3.

To install dependencies, run:
```bash
pip3 install -r requirements.txt
```
To start the software package run the file `main.py`.

If you do not have a radio plugged in or you do have a radio but do not want to send real life commands, then add the `--no_radio` flag. 

If you do not have a refbox running or you want to ignore commands from the refbox, then add the `--no_refbox` flag. 

If you want to use the simulator rather than a real field (with camera) then add the `--simulate` flag.

For more information on the flags available run 
```
python3 main.py --help
```

If you are just getting started with developing our software, likely you will want to run:
```bash
python3 main.py --simulate --no_refbox
```
If running with vision (i.e not using the simulator), ssl-vision must be running
https://docs.google.com/document/d/1i-Pybv2wBhN23FT94PiGMyX6yAJglqeaCds62TX8-7o/edit

### Referee box
In order to control a full game (with scoring, fouls, corners, penalties etc.) you should have a refbox running. This isn't necessary for testing and general development.

Follow [these](https://robocup-ssl.github.io/ssl-refbox/install.html) instructions to install and run the refbox.

Messages from the refbox are stored in the `gamestate.latest_refbox_message` variable. If you do not have a refbox running, then this variable will be `None`.
### NOTES FOR MAC

TODO: For mac users, installing pygame for python3 may require more steps

On Mac, not all versions of python3 in pygame are compatible. We know that python 3.7.5 and pygame 1.9.6 will work. If you have a version higher than 3.7.5 and need to downgrade, follow this link. https://inneka.com/programming/python/how-to-downgrade-python-from-3-7-to-3-6/

The easiest may be to follow solution 4 and create a virtual environment, which you may have to install anaconda for.

Inside the venv, run
```bash
python3 -m pip install -r requirements.txt
```

### NOTES FOR WINDOWS

NOTE: For dealing with issues installing Python 3 on Windows: https://stackoverflow.com/questions/47539201/python-is-not-recognized-windows-10. Your path will most likely be "C:\Users\AppData\Local\Programs\Python\Python38" if you installed Python 3.8.

In windows, type python instead of python3

```bash
python main.py
```
