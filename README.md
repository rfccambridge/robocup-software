# Robocup Software
https://docs.google.com/document/d/1Eim1MRx77IE2ieGvYYDAL3BJYKYtR9JhJai6PuHB-iw/edit

To install dependencies, run:
```bash
pip install -r requirements.txt
```
Main control loop is main.py - comment out vision + comms threads if not running with hardware
```bash
python3 main.py
```
If running with vision, ssl-vision must be running
https://docs.google.com/document/d/1i-Pybv2wBhN23FT94PiGMyX6yAJglqeaCds62TX8-7o/edit

__Python 3__ is required, due to compatibility issues with the pyserial module.
