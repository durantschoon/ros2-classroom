@echo off
:: ROS 2 Classroom - Windows One-Click Launcher
:: Prerequisite: Docker Desktop must be installed and running.
:: Download Docker Desktop: https://docs.docker.com/desktop/install/windows-install/
:: This script bypasses default PowerShell execution policies to run the native Windows setup.

PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0ros2.ps1' %*"
if %ERRORLEVEL% neq 0 (
    echo.
    pause
)
