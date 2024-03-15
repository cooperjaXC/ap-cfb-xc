# Setup python virtual environments for Windows

<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

To run the script test.py with a virtual python environment, 
double click/execute the test.bat file.
That's it.

- Here, test.py and .bat are stand-ins for a real python file with installation requirements you are trying to run. 
Edit the `test.py` reference in `test.bat` to point to the script you hope to run.

To simply set up the venv itself, just execute the `setup.bat` file.

## Requirements

Ensure the base python interpreter path designated in `set_python_path.bat`
is set to your desired python.exe.

- Package dependencies may require a minimum python version. 
Tip: use the latest version of python you have available. 

### Notes
- Conda environments may experience issues installing with `ssl` DLL issues.
