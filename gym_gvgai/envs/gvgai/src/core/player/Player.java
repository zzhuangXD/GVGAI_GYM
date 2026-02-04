package core.player;

import core.game.Game;
import core.game.StateObservation;
import core.game.StateObservationMulti;
import ontology.Types;
import tools.ElapsedCpuTimer;
import tools.com.google.gson.Gson;
import tools.com.google.gson.GsonBuilder;
import core.game.Observation;
import core.vgdl.VGDLRegistry;
import java.awt.*;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.HashSet;
import java.util.stream.Collectors;
import java.util.Queue;
import java.util.LinkedList;

public abstract class Player {

    private int playerID;
    private String actionFile;
    private BufferedWriter writer;
    private static final boolean SHOULD_LOG = true;
    private Types.ACTIONS lastAction = null;
    private int randomSeed;
    private boolean isHuman;
    private Map<String, String> dynamicCharMapping = new HashMap<>();
    private Set<String> usedSymbols = new HashSet<>();
    private boolean symbolsInitialized = false;

    // New data structure to store action and state together.
    private static class TurnData {
        Types.ACTIONS action;
        StateObservation state;

        TurnData(Types.ACTIONS action, StateObservation state) {
            this.action = action;
            this.state = state;
        }
    }
    private ArrayList<TurnData> recordedTurns;


    public abstract Types.ACTIONS act(StateObservation stateObs, ElapsedCpuTimer elapsedTimer);
    public abstract Types.ACTIONS act(StateObservationMulti stateObs, ElapsedCpuTimer elapsedTimer);

    public void result(StateObservation stateObs, ElapsedCpuTimer elapsedCpuTimer) {
        // This method is called after an action is executed.
    }

    public void resultMulti(StateObservationMulti stateObs, ElapsedCpuTimer elapsedCpuTimer) {
        // This method is called after an action is executed in a multiplayer game.
    }

    public void setup(String actionFile, int randomSeed, boolean isHuman) {
        this.actionFile = actionFile;
        this.randomSeed = randomSeed;
        this.isHuman = isHuman;
        if (this.actionFile != null && SHOULD_LOG) {
            recordedTurns = new ArrayList<>();
        }
    }

    private void initializeSymbols(Game played) {
        if (!symbolsInitialized) {
            synchronized (this) {
                if (!symbolsInitialized) {
                    for (Character c : played.getCharMapping().keySet()) {
                        usedSymbols.add(String.valueOf(c));
                    }
                    symbolsInitialized = true;
                }
            }
        }
    }

    private String getSpriteSymbol(String spriteName, Map<String, Character> reverseCharMapping, char backgroundChar) {
        // 1. Check predefined LevelMapping
        if (reverseCharMapping.containsKey(spriteName)) {
            return String.valueOf(reverseCharMapping.get(spriteName));
        }

        // 2. Check our own dynamic mapping
        if (dynamicCharMapping.containsKey(spriteName)) {
            return dynamicCharMapping.get(spriteName);
        }

        // 3. If not found, create a new dynamic mapping
        synchronized (this) {
            // Double-check to prevent race conditions
            if (dynamicCharMapping.containsKey(spriteName)) {
                return dynamicCharMapping.get(spriteName);
            }

            // Find the first available character starting from 'A'
            char nextChar = 'A';
            while (usedSymbols.contains(String.valueOf(nextChar))) {
                nextChar++;
            }
            String newSymbol = String.valueOf(nextChar);

            // Save the new mapping
            dynamicCharMapping.put(spriteName, newSymbol);
            usedSymbols.add(newSymbol);

            return newSymbol;
        }
    }

    private ArrayList<ArrayList<String>> convertStateToMap(StateObservation stateObs, Game played) {
        initializeSymbols(played);

        ArrayList<ArrayList<String>> mapList = new ArrayList<>();
        if (stateObs == null) {
            return mapList;
        }

        // Use the existing reverse char mapping to find the background character.
        Map<String, Character> reverseCharMapping = new HashMap<>();
        for (Map.Entry<Character, ArrayList<String>> entry : played.getCharMapping().entrySet()) {
            for (String spriteName : entry.getValue()) {
                reverseCharMapping.put(spriteName, entry.getKey());
            }
        }
        char backgroundChar = reverseCharMapping.getOrDefault("background", '.');
        core.vgdl.VGDLRegistry registry = core.vgdl.VGDLRegistry.GetInstance();

        ArrayList<Observation>[][] grid = stateObs.getObservationGrid();
        if (grid != null && grid.length > 0) {
            // The grid is organized by [x][y], but we want to build the map row by row (y-first).
            int width = grid.length;
            int height = grid[0].length;

            for (int y = 0; y < height; y++) {
                ArrayList<String> rowList = new ArrayList<>();
                for (int x = 0; x < width; x++) {
                    ArrayList<Observation> cell = grid[x][y];
                    if (cell != null && !cell.isEmpty()) {
                        // Get the last observation in the list, which should be the one on top.
                        Observation topObs = cell.get(cell.size() - 1);
                        String spriteName = registry.getRegisteredSpriteKey(topObs.itype);
                        String spriteRepresentation = getSpriteSymbol(spriteName, reverseCharMapping, backgroundChar);
                        rowList.add(spriteRepresentation);
                    } else {
                        rowList.add(String.valueOf(backgroundChar));
                    }
                }
                mapList.add(rowList);
            }
        }
        return mapList;
    }


    final public void teardown(Game played, String gameName) {
        try {
            if ((this.actionFile != null && !actionFile.equals("")) && SHOULD_LOG) {
                Map<String, Object> finalJson = new LinkedHashMap<>();

                // 1. Game Summary
                Map<String, Object> summary = new LinkedHashMap<>();
                summary.put("randomSeed", randomSeed);
                summary.put("winner", played.getWinner() == Types.WINNER.PLAYER_WINS ? 1 : 0);
                summary.put("score", played.getScore());
                summary.put("gameTick", played.getGameTick());
                finalJson.put("summary", summary);

                // Add dynamic mapping to the JSON output
                finalJson.put("dynamic_mapping", dynamicCharMapping);

                // 2. Process recorded turns into the desired actions format
                ArrayList<Map<String, Object>> actionsList = new ArrayList<>();
                int actionIndex = 1;
                for (TurnData turn : recordedTurns) {
                    Map<String, Object> actionRecord = new LinkedHashMap<>();
                    actionRecord.put("action_index", actionIndex++);
                    actionRecord.put("action", turn.action.toString());
                    actionRecord.put("score", turn.state.getGameScore());

                    // Get alien counts from the StateObservation's NPC list
                    int numAliens = 0;
                    ArrayList<Observation>[] npcPositions = turn.state.getNPCPositions();

//                 --- START of DEBUGGING ---
//                 Show how we count the number of a type of NPC
//                 if (actionIndex == 286 && npcPositions != null) { // Only Print at index = 286
//                     System.out.println("--- Debugging action_index: " + actionIndex + " ---");
//                     System.out.println("npcPositions array length: " + npcPositions.length);
//                     int listIndex = 0;
//                     for (ArrayList<Observation> npcList : npcPositions) {
//                         if (npcList != null && !npcList.isEmpty()) {
//                             System.out.println("  List " + listIndex + " (itype: " + npcList.get(0).itype + "): contains " + npcList.size() + " objects.");
//                             for (Observation npc : npcList) {
//                                 System.out.println("    -> " + npc.toString());
//                             }
//
//                         } else {
//                              System.out.println("  List " + listIndex + ": is empty or null.");
//                         }
//                         listIndex++;
//                     }
//                     System.out.println("------------------------------------");
//                 }
//                 --- END ---

                    // 0 Aliens
                    if(gameName.equals("aliens")){
                        if (npcPositions != null) {
                            int alienGreenId = VGDLRegistry.GetInstance().getRegisteredSpriteValue("alienGreen");
                            int alienBlueId = VGDLRegistry.GetInstance().getRegisteredSpriteValue("alienBlue");

                            for (ArrayList<Observation> npcList : npcPositions) {
                                if (npcList != null) {
                                    for (Observation npc : npcList) {
                                        if (npc.itype == alienGreenId || npc.itype == alienBlueId) {
                                            numAliens++;
                                        }
                                    }
                                }
                            }
                        }

                        actionRecord.put("num_of_aliens", numAliens);
                    }


                    // 1 Escape
                    if(gameName.equals("escape")){
                        actionRecord.put("escaper", 0);
                    }




                    // END OF GAMES
                    ArrayList<ArrayList<String>> map = convertStateToMap(turn.state, played);
                    actionRecord.put("map", map);

                    actionsList.add(actionRecord);
                }
                finalJson.put("actions", actionsList);

                // Write JSON to file
                writer = new BufferedWriter(new FileWriter(new File(this.actionFile)));
                Gson gson = new GsonBuilder().create(); // Compact JSON

                // Manual pretty printing for the desired format
                writer.write("{\n");
                writer.write("  \"summary\": " + gson.toJson(finalJson.get("summary")) + ",\n");
                writer.write("  \"dynamic_mapping\": " + gson.toJson(finalJson.get("dynamic_mapping")) + ",\n");

                writer.write("  \"actions\": [\n");
                for (int i = 0; i < actionsList.size(); i++) {
                    writer.write("    " + gson.toJson(actionsList.get(i)));
                    if (i < actionsList.size() - 1) {
                        writer.write(",\n");
                    } else {
                        writer.write("\n");
                    }
                }
                writer.write("  ]\n");

                writer.write("}\n");
                writer.close();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
     * Logs the action and the state it was decided upon.
     * This is the new primary logging method.
     * @param action The action taken.
     * @param state The state before the action was taken.
     */
    final public void logAction(Types.ACTIONS action, StateObservation state) {
        lastAction = action;
        if (this.actionFile != null && SHOULD_LOG) {
            recordedTurns.add(new TurnData(action, state.copy()));
        }
    }
    
    /**
     * Deprecated: Use logAction(action, state) instead to capture map state.
     * This method is kept for backward compatibility but will not log states.
     */
    @Deprecated
    final public void logAction(Types.ACTIONS action) {
        lastAction = action;
        // Does not log to recordedTurns to avoid incomplete data.
    }


    public Types.ACTIONS getLastAction() {
        return lastAction;
    }

    public boolean isHuman() {
        return isHuman;
    }

    public int getPlayerID() {
        return playerID;
    }

    public void setPlayerID(int id) {
        playerID = id;
    }

    public ArrayList<Types.ACTIONS> getAllActions() {
        if (recordedTurns == null) {
            return new ArrayList<>();
        }
        ArrayList<Types.ACTIONS> actions = new ArrayList<>();
        for (TurnData turn : recordedTurns) {
            actions.add(turn.action);
        }
        return actions;
    }

    public void draw(Graphics2D g) {
        // Overwrite this method in your controller to draw on the screen.
    }
}
