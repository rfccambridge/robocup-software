# Robocup Software
https://docs.google.com/document/d/1Eim1MRx77IE2ieGvYYDAL3BJYKYtR9JhJai6PuHB-iw/edit

__Python 3__ is required, due to compatibility issues with the pyserial module.
In some cases, you may have to use python and pip commands without the 3.

To install dependencies, run:
```bash
pip3 install -r requirements.txt
```
Main control loop is main.py - comment out vision + comms threads if not running with hardware
```bash
python3 main.py
```
If running with vision, ssl-vision must be running
https://docs.google.com/document/d/1i-Pybv2wBhN23FT94PiGMyX6yAJglqeaCds62TX8-7o/edit

# NOTES FOR MAC

TODO: For mac users, installing pygame for python3 may require more steps

On Mac, not all versions of python3 in pygame are compatible. We know that python 3.7.5 and pygame 1.9.6 will work. If you have a version higher than 3.7.5 and need to downgrade, follow this link. https://inneka.com/programming/python/how-to-downgrade-python-from-3-7-to-3-6/

The easiest may be to follow solution 4 and create a virtual environment, which you may have to install anaconda for.

Inside the venv, run
```bash
python3 -m pip install -r requirements.txt
```

# NOTES FOR WINDOWS

NOTE: For dealing with issues installing Python 3 on Windows: https://stackoverflow.com/questions/47539201/python-is-not-recognized-windows-10. Your path will most likely be "C:\Users\AppData\Local\Programs\Python\Python38" if you installed Python 3.8.

In windows, type python instead of python3

```bash
python main.py
```
