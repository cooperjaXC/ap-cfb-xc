:: rem @set PYTHON_PATH="C:\Users\johncooper\AppData\Local\Programs\Python\Python38\python.exe"
rem Make sure you paste your base python interpreter path in the py_venv\set_python_path.bat file!
:: Base python interpreter downloads
::@set PYTHON_PATH="C:\Users\Jacob.Cooper\AppData\Local\Programs\Python\Python310\python.exe"
::@set PYTHON_PATH="C:\\Users\\acc-s\\AppData\\Local\\Programs\\Python\\Python37\\python.exe"
:: Dynamically set the python path for base downloaded python interpreters
:: Just set which version of python you're using
::@set "PYTHON_VERSION=3.7"
@set "PYTHON_VERSION=3.10"
@set PYTHON_PATH="%USERPROFILE%\AppData\Local\Programs\Python\Python%PYTHON_VERSION:.=%\python.exe"
::
:: ArcGIS python path
::: If you have recently updated your ArcGIS Pro and subsequently your python interpreter,
::: you may need to follow these steps if you encounter an `ensurepip` error:
::: https://stackoverflow.com/questions/71395733/python-package-creation-on-windows-fails-with-python-exe-im-ensurepip/72192474#72192474
::@set PYTHON_PATH="C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
::
:: Anaconda Python path
:: @set PYTHON_PATH="C:\Users\Jacob.Cooper\Anaconda3\python.exe"
::
echo %PYTHON_PATH%
:: echo %PYTHON_PATH% /switch1 /switch2
