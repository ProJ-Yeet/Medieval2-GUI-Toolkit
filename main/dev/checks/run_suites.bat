@echo off
rem Runs the test suites hidden in the background: no console window, and no
rem browser tab (the suites run with UT_NO_BROWSER=1).
rem
rem   run_suites.bat                        every suite
rem   run_suites.bat test_cas test_edbimport   just these
rem
rem When it is done, suite_report.txt beside this file lists what failed. While
rem it runs, that file says RUNNING.
setlocal
set "PY="
for %%c in (py python python3) do (
    if not defined PY (
        %%c -c "import sys" >nul 2>nul
        if not errorlevel 1 set "PY=%%c"
    )
)
if not defined PY (
    echo No Python found. Install Python 3.10 or newer from python.org.
    pause
    exit /b 1
)
for /f "delims=" %%p in ('%PY% -c "import sys,pathlib;p=pathlib.Path(sys.executable);w=p.with_name('pythonw.exe');print(w if w.is_file() else p)"') do set "PYW=%%p"
start "" "%PYW%" "%~dp0run_suites.py" %*
echo The suites are running in the background.
echo The report will be in: %~dp0suite_report.txt
"%SystemRoot%\System32\timeout.exe" /t 4 >nul
