@echo off
REM Setup script for manual scraper conda environment
echo Creating conda environment: manual-scraper

conda create -n manual-scraper python=3.11 -y

echo.
echo Activating environment...
call conda activate manual-scraper

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete! Environment 'manual-scraper' is ready.
echo.
echo To activate the environment, run:
echo     conda activate manual-scraper
echo.
echo To run the scraper:
echo     python scraper.py

