package tracks.singlePlayer.optimized_mcts;

import java.io.FileReader;
import java.util.ArrayList;
import java.util.List;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;

/**
 * A class to read configuration parameters from an external JSON file.
 * It supports the following keys:
 * - gameList (List<String>)
 * - algorithmList (List<String>)
 * - cpuCores (int)
 * - mctsIterations (int)
 * - timeBudgetMillis (long)
 * - maxSteps (int)
 */
public class Config {
    public List<String> gameList;
    public List<String> algorithmList;
    public int cpuCores;
    public int mctsIterations;
    public long timeBudgetMillis;
    public int maxSteps;

    @SuppressWarnings("unchecked")
    public Config(String configPath) {
        JSONParser parser = new JSONParser();
        try (FileReader reader = new FileReader(configPath)) {
            JSONObject config = (JSONObject) parser.parse(reader);

            JSONArray games = (JSONArray) config.get("gameList");
            gameList = new ArrayList<>();
            if (games != null) {
                for (Object game : games) {
                    gameList.add((String) game);
                }
            }

            JSONArray algorithms = (JSONArray) config.get("algorithmList");
            algorithmList = new ArrayList<>();
            if (algorithms != null) {
                for (Object algo : algorithms) {
                    algorithmList.add((String) algo);
                }
            }

            Object iterations = config.get("mctsIterations");
            if (iterations instanceof Number) {
                mctsIterations = ((Number) iterations).intValue();
            } else {
                mctsIterations = 10000;
            }

            Object cores = config.get("cpuCores");
            if (cores instanceof Number) {
                cpuCores = ((Number) cores).intValue();
            } else {
                cpuCores = 1;
            }

            Object timeBudget = config.get("timeBudgetMillis");
            if (timeBudget instanceof Number) {
                timeBudgetMillis = ((Number) timeBudget).longValue();
            } else {
                timeBudgetMillis = 200;
            }

            Object steps = config.get("maxSteps");
            if (steps instanceof Number) {
                maxSteps = ((Number) steps).intValue();
            } else {
                maxSteps = 500;
            }
        } catch (Exception e) {
            e.printStackTrace();
            // Default configuration on error
            gameList = new ArrayList<>();
            gameList.add("DefaultGame");
            algorithmList = new ArrayList<>();
            algorithmList.add("OptimizedMCTS");
            cpuCores = 1;
            mctsIterations = 10000;
            timeBudgetMillis = 200;
            maxSteps = 500;
        }
    }
}
