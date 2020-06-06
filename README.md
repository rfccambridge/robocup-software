# Robocup Software

## Documentation

![Continuous Integration](https://github.com/rfccambridge/robocup-software/workflows/Continuous%20Integration/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/robocup-docs/badge/?version=latest)](https://robocup-docs.readthedocs.io/en/latest/?badge=latest)

Online Function Reference: <https://robocup-docs.readthedocs.io/>

Codebase Description: <https://docs.google.com/document/d/1Eim1MRx77IE2ieGvYYDAL3BJYKYtR9JhJai6PuHB-iw/edit>

## Development

When developing, make sure that all test cases pass and the linter doesn't
complain before you send a pull request! For the linter and tests, run these
commands respectively.
__Highly recommend that you have a linting extension in our code editor.__
We use Flake8.

```bash
flake8
```

```bash
pytest -v
```

If you are __sure__ that what you are writing is not a linting error,
then feel free to add a comment `# noqa` at the end of the line and the
linter will ignore it in the CI.
Please make sure that you do not merge until the linter on Github gives a
green check.

Make sure you are in the root directory before running.
If it says flake8 not found, install it.

```bash
pip3 install flake8
```

## Setup

__Python 3__ (version 3.6 or above), and __Linux__ are required (Ubuntu 16.0.4 or above).

For Windows/Mac users, it might be rough to get things working natively. Installing a virtual machine such as VMWare is one option - you may need to allocate multiple cores if it's too slow.

To install dependencies, run:

```bash
pip3 install -r requirements.txt
```

To start the software package run the file `main.py`.
To see logging, run `cutelog` separately.

If you are just getting started with developing our software, likely you will want to run:

```bash
python3 main.py --simulate --no_refbox --debug
```

If you want to use the simulator rather than a real field (with camera) then add the `--simulate` flag.

If you are running on a real field but do not want to send commands to physical robots, then add the `--no_radio` flag.

If you do not have a refbox running or you want to ignore commands from the refbox, then add the `--no_refbox` flag.

If you want to run a particular strategy for the home team, add `hs {strategy name}`.

For more information on the flags available run

```bash
python3 main.py --help
```

If running with vision (i.e not using the simulator), ssl-vision must be running
<https://docs.google.com/document/d/1i-Pybv2wBhN23FT94PiGMyX6yAJglqeaCds62TX8-7o/edit>

### Referee box

In order to control a full game (with scoring, fouls, corners, penalties etc.) you should have a refbox running. This isn't necessary for testing and general development.

Follow [these](https://robocup-ssl.github.io/ssl-refbox/install.html) instructions to install and run the refbox.
Refbox usage instructions are [here](https://robocup-ssl.github.io/ssl-refbox/manual.html). (Note that you must name the teams first!)

## Insalling on Other Platforms

WINDOWS/MAC MAY BE A STRUGGLE - WE RECOMMEND LINUX

### NOTES FOR MAC

TODO: For mac users, installing pygame for python3 may require more steps

On Mac, not all versions of python3 in pygame are compatible. We know that python 3.7.5 and pygame 1.9.6 will work. If you have a version higher than 3.7.5 and need to downgrade, follow this link. <https://inneka.com/programming/python/how-to-downgrade-python-from-3-7-to-3-6/>

The easiest may be to follow solution 4 and create a virtual environment, which you may have to install anaconda for.

Inside the venv, run

```bash
python3 -m pip install -r requirements.txt
```

### NOTES FOR WINDOWS

NOTE: For dealing with issues installing Python 3 on Windows: <https://stackoverflow.com/questions/47539201/python-is-not-recognized-windows-10.> Your path will most likely be "C:\Users\AppData\Local\Programs\Python\Python38" if you installed Python 3.8.

In windows, type python instead of python3

```bash
python main.py --simulate --no_refbox --debug
```
