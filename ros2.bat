@echo off
:: ROS 2 Classroom - Windows One-Click Launcher
:: This script bypasses default PowerShell execution policies to run the native Windows setup.

PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0ros2.ps1' %*"
