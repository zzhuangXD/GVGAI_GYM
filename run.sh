#!/bin/bash
set -e

# Change to the script's directory to ensure relative paths work
cd "$(dirname "$0")"

echo "Creating bin directory..."
mkdir -p bin

echo "Finding and compiling Java source files..."
find gym_gvgai/envs/gvgai/src -name "*.java" > sources.txt
javac -cp "lib/json-simple-1.1.1.jar" -d bin -sourcepath gym_gvgai/envs/gvgai/src @sources.txt


echo "Compilation successful. Running test..."
java -cp "bin:lib/json-simple-1.1.1.jar" tracks.singlePlayer.Test

echo "Cleaning up..."
rm sources.txt

echo "run.sh finished successfully."
