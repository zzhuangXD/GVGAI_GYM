@echo off

dir /s /b gym_gvgai*.java > sources.txt
javac -d bin @sources.txt
if errorlevel 1 (
    echo Compilation failed.
    pause
    exit /b 1
)
del sources.txt
rem Run Test class
java -cp bin tracks.singlePlayer.Test
pause
