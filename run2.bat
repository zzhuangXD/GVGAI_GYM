@echo off
echo --- Setting up Environment for Optimized MCTS Agent ---

rem Classpath for compilation (only external libraries)
set COMPILE_CP=lib\json-simple-1.1.1.jar

rem Classpath for runtime (our compiled code + external libraries)
set RUNTIME_CP=bin;lib\json-simple-1.1.1.jar

echo.
echo --- Compiling All Java Sources... ---
rem Find ALL .java files in the project and compile them into the 'bin' directory
dir /s /b gym_gvgai\envs\gvgai\src*.java > sources.txt
javac -encoding UTF-8 -sourcepath gym_gvgai\envs\gvgai\src -cp %COMPILE_CP% -d bin @sources.txt

rem Check if compilation was successful
if errorlevel 1 (
    echo.
    echo --- COMPILATION FAILED ---
    echo Please check the error messages above.
    del sources.txt
    pause
    exit /b 1
)

del sources.txt
echo --- Compilation Successful! ---
echo.

echo --- LAUNCHING AGENT ON ALIENS ---
rem Run the competition framework with the specified game and our Optimized MCTS agent
java -cp %RUNTIME_CP% core.competition.AgentExecutor gym_gvgai\envs\games\aliens_v0\aliens.txt gym_gvgai\envs\games\aliens_v0\aliens_lvl0.txt tracks.singlePlayer.optimized_mcts.OptimizedMCTS null

echo.
echo --- Game Finished ---
pause