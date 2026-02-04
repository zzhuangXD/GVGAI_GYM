#!/bin/bash
set -e

# Change to the script's directory to ensure relative paths work
cd "$(dirname "$0")"

echo "--- Setting up Environment for Optimized MCTS Agent ---"

# Classpath for compilation (only external libraries)
COMPILE_CP="lib/json-simple-1.1.1.jar"

# Classpath for runtime (our compiled code + external libraries)
RUNTIME_CP="bin:lib/json-simple-1.1.1.jar"

echo ""
echo "--- Compiling All Java Sources... ---"
# Find ALL .java files in the project and compile them into the 'bin' directory
find gym_gvgai/envs/gvgai/src -name "*.java" > sources.txt
find gym_gvgai/envs/gvgai/src/tracks/singlePlayer/optimized_mcts -name "*.java" >> sources.txt
javac -encoding UTF-8 -sourcepath gym_gvgai/envs/gvgai/src -cp $COMPILE_CP -d bin @sources.txt

# Check if compilation was successful
if [ $? -ne 0 ]; then
    echo ""
    echo "--- COMPILATION FAILED ---"
    echo "Please check the error messages above."
    rm sources.txt
    exit 1
fi

rm sources.txt
echo "--- Compilation Successful! ---"
echo ""

echo "--- LAUNCHING AGENT ON ESCAPE ---"
# Run the competition framework with the specified game and our Optimized MCTS agent
#java -cp $RUNTIME_CP core.competition.AgentExecutor gym_gvgai/envs/games/sokoban_v0/sokoban.txt gym_gvgai/envs/games/sokoban_v0/sokoban_lvl0.txt tracks.singlePlayer.optimized_mcts.OptimizedMCTS ./dataset/sokoban/output.txt
#java -cp $RUNTIME_CP core.competition.AgentExecutor gym_gvgai/envs/games/zelda_v0/zelda.txt gym_gvgai/envs/games/zelda_v0/zelda_lvl4.txt tracks.singlePlayer.optimized_mcts.OptimizedMCTS ./dataset/zelda/output_L4.txt
#java -cp $RUNTIME_CP core.competition.AgentExecutor gym_gvgai/envs/games/escape_v0/escape.txt gym_gvgai/envs/games/escape_v0/escape_lvl0.txt tracks.singlePlayer.optimized_mcts.OptimizedMCTS ./dataset/escape/output.txt
java -cp $RUNTIME_CP core.competition.AgentExecutor gym_gvgai/envs/games/aliens_v0/aliens.txt gym_gvgai/envs/games/aliens_v0/aliens_lvl4.txt tracks.singlePlayer.optimized_mcts.OptimizedMCTS ./dataset/aliens/output_L4.txt

echo ""
echo "--- Game Finished ---"
echo ""

python3 dataset/escape/format_output.py
echo "--- Formatting Complete ---"
