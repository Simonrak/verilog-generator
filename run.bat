@echo off
setlocal enabledelayedexpansion

:: Start execution
goto :main

:: Function definitions
:check_root_directory
if not exist "setup.py" (
    echo Error: Must be run from project root directory containing setup.py
    exit /b 1
)
if not exist "mmio" (
    echo Error: Must be run from project root directory containing mmio package
    exit /b 1
)
goto :eof

:: Function to initialize environment variables
:init_environment
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"
set "DEV_MODE="
if "%~1"=="--dev" set "DEV_MODE=1"
set "IS_POWERSHELL="
if defined PSModulePath set "IS_POWERSHELL=1"
goto :eof

:: Function to verify and install Python if needed
:check_python
echo Checking Python installation...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found, attempting automatic installation...
    
    :: Try winget installation
    winget --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Installing Python using winget...
        winget install Python.Python.3.13 --accept-source-agreements --accept-package-agreements
        if %errorlevel% equ 0 (
            echo Python installed successfully
            :: Refresh environment variables
            refreshenv.cmd >nul 2>&1
            goto :eof
        )
    )
    
    echo.
    echo Error: Could not automatically install Python
    echo Please install Python 3.13 or later manually from:
    echo https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH" during installation
    pause
    exit /b 1
)
goto :eof

:: Function to create/verify virtual environment
:setup_venv
if not exist "%BASE_DIR%.venv" (
    echo Creating virtual environment...
    py -3 -m venv "%BASE_DIR%.venv" >nul 2>venv_error.tmp
    if %errorlevel% neq 0 (
        type venv_error.tmp
        del venv_error.tmp
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
    del venv_error.tmp
    echo Virtual environment created
) else if not exist "%BASE_DIR%.venv\Scripts\python.exe" (
    echo Virtual environment exists but appears invalid. Recreating...
    rmdir /s /q "%BASE_DIR%.venv"
    call :setup_venv
    exit /b %errorlevel%
)
goto :eof

:: Function to activate virtual environment
:activate_venv
echo Activating virtual environment...
if defined IS_POWERSHELL (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%BASE_DIR%.venv\Scripts\Activate.ps1'" >nul 2>activate_error.tmp
) else (
    call "%BASE_DIR%.venv\Scripts\activate.bat" >nul 2>activate_error.tmp
)
if %errorlevel% neq 0 (
    type activate_error.tmp
    del activate_error.tmp
    echo Failed to activate virtual environment
    pause
    exit /b 1
)
del activate_error.tmp
set "PYTHON=%BASE_DIR%.venv\Scripts\python.exe"
echo Virtual environment activated
goto :eof

:: Function to upgrade pip
:upgrade_pip
echo Upgrading pip...
"%PYTHON%" -m pip install --upgrade pip >nul 2>pip_upgrade_error.tmp
if %errorlevel% neq 0 (
    type pip_upgrade_error.tmp
    del pip_upgrade_error.tmp
    echo Failed to upgrade pip
    pause
    exit /b 1
)
del pip_upgrade_error.tmp
echo Pip upgrade complete
goto :eof

:: Function to run setup.py
:run_setup
echo Running setup.py...
if defined DEV_MODE (
    echo Installing in development mode...
    "%PYTHON%" -m pip install -e ".[dev]" >nul 2>setup_error.tmp
) else (
    "%PYTHON%" -m pip install -e "." >nul 2>setup_error.tmp
)
if %errorlevel% neq 0 (
    type setup_error.tmp
    del setup_error.tmp
    echo Failed to run setup.py
    pause
    exit /b 1
)
del setup_error.tmp
echo Setup complete
goto :eof


:: Function to run the application
:run_application
echo Running mmio package...
"%PYTHON%" -m mmio 2>mmio_error.tmp
if %errorlevel% neq 0 (
    type mmio_error.tmp
    del mmio_error.tmp
    echo Failed to run mmio package
    exit /b 1
)
del mmio_error.tmp
echo Application ran successfully
goto :eof

:: Function to display activation instructions
:show_activation_instructions
echo.
if defined IS_POWERSHELL (
    echo To activate the virtual environment manually, run: %BASE_DIR%.venv\Scripts\Activate.ps1
) else (
    echo To activate the virtual environment manually, run: %BASE_DIR%.venv\Scripts\activate.bat
)
goto :eof

:: Main execution flow
:main
call :check_root_directory
if %errorlevel% neq 0 exit /b %errorlevel%

call :init_environment %*
if %errorlevel% neq 0 exit /b %errorlevel%

call :check_python
if %errorlevel% neq 0 exit /b %errorlevel%

call :setup_venv
if %errorlevel% neq 0 exit /b %errorlevel%

call :activate_venv
if %errorlevel% neq 0 exit /b %errorlevel%

call :upgrade_pip
if %errorlevel% neq 0 exit /b %errorlevel%

call :run_setup
if %errorlevel% neq 0 exit /b %errorlevel%

call :run_application
if %errorlevel% neq 0 exit /b %errorlevel%

call :show_activation_instructions
echo Installation completed successfully!
goto :eof

endlocal 