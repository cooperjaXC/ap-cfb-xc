:: Set your root directory that houses your virtual environment content.
::@set VENV_DIR=.
:: Set the default for this to be the directory this .bat file is housed within.
@set VENV_DIR=%~dp0
@call %VENV_DIR%\set_python_path.bat
@%PYTHON_PATH% %VENV_DIR%\setup.py
