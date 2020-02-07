# Robocup Software
https://docs.google.com/document/d/1Eim1MRx77IE2ieGvYYDAL3BJYKYtR9JhJai6PuHB-iw/edit

__Python 3__ is required, due to compatibility issues with the pyserial module.
In some cases, you may have to use python and pip commands without the 3.

To install dependencies, run:
```bash
pip3 install -r requirements.txt
```
TODO: For mac users, installing pygame for python3 may require more steps

Main control loop is main.py - comment out vision + comms threads if not running with hardware
```bash
python3 main.py
```
If running with vision, ssl-vision must be running
https://docs.google.com/document/d/1i-Pybv2wBhN23FT94PiGMyX6yAJglqeaCds62TX8-7o/edit

NOTE: For dealing with issues installing Python 3 on Windows: https://stackoverflow.com/questions/47539201/python-is-not-recognized-windows-10. Your path will most likely be "C:\Users\AppData\Local\Programs\Python\Python38" if you installed Python 3.8.
