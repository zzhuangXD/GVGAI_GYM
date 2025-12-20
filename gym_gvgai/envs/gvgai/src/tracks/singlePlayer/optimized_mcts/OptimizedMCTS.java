package tracks.singlePlayer.optimized_mcts;

import java.io.FileWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import org.json.simple.JSONObject;
import core.game.StateObservation;
import core.player.AbstractPlayer;
import ontology.Types;
import tools.ElapsedCpuTimer;

public class OptimizedMCTS extends AbstractPlayer {

    private Config config;
    private Random random;
    private List<String> actionSequence = new ArrayList<>();
    private ConcurrentHashMap<Long, StateValue> transpositionTable;
    private ExecutorService executor;

    /**
     * Inner class to store state values个 in the transposition table in a thread-safe manner.
     */
    public static class StateValue {
        public int n_visits = 0;
        public double tot_value = 0;
        public synchronized void update(double value) {
            this.tot_value += value;
            this.n_visits++;
        }
    }

    public OptimizedMCTS(StateObservation stateObs, ElapsedCpuTimer elapsedTimer) {
        this.config = new Config("gym_gvgai/envs/gvgai/src/tracks/singlePlayer/optimized_mcts/config.json");
        this.random = new Random();
        this.transpositionTable = new ConcurrentHashMap<>();
        this.executor = Executors.newFixedThreadPool(this.config.cpuCores);
    }

    @Override
    public Types.ACTIONS act(StateObservation stateObs, ElapsedCpuTimer elapsedTimer) {
        Node root = new Node(stateObs, null, null);
        runMCTS(elapsedTimer, root);

        Node bestChild = null;
        int mostVisits = -1;
        for (Node child : root.children) {
            StateValue stats = transpositionTable.get((long) child.state.hashCode());
            if (stats != null && stats.n_visits > mostVisits) {
                mostVisits = stats.n_visits;
                bestChild = child;
            }
        }
        
        Types.ACTIONS chosenAction = (bestChild != null) ? bestChild.action : stateObs.getAvailableActions().get(0);
        actionSequence.add(chosenAction.toString());

        // Log the state and the chosen action for JSON output.
        this.logAction(chosenAction, stateObs);

        if (stateObs.isGameOver()) {
            outputResults(actionSequence, stateObs.getGameWinner() == Types.WINNER.PLAYER_WINS, stateObs.getGameScore());
        }
        return chosenAction;

    }

    private void runMCTS(ElapsedCpuTimer elapsedTimer, Node root) {
        long remainingTime = elapsedTimer.remainingTimeMillis();
        long timeLimit = Math.min(config.timeBudgetMillis, remainingTime - 15);
        long startTime = System.currentTimeMillis();
        
        System.out.println("Starting parallel MCTS with " + config.cpuCores + " cores. Time budget: " + timeLimit + "ms, max iterations: " + config.mctsIterations);

        List<Runnable> tasks = new ArrayList<>();
        for (int i = 0; i < config.mctsIterations; i++) {
            tasks.add(() -> {
                Node selectedNode = select(root);
                if (selectedNode.state.isGameOver()) {
                    selectedNode.backpropagate(getScore(selectedNode.state), transpositionTable);
                    return;
                }
                Node newNode = selectedNode.expand();
                if(newNode != null) {
                    double result = simulate(newNode);
                    newNode.backpropagate(result, transpositionTable);
                } else {
                    selectedNode.backpropagate(getScore(selectedNode.state), transpositionTable);
                }
            });
        }
        
        try {
            executor.invokeAll(tasks.stream().map(Executors::callable).collect(Collectors.toList()), timeLimit, TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        StateValue rootStats = transpositionTable.get((long) root.state.hashCode());
        int totalVisits = (rootStats != null) ? rootStats.n_visits : 0;
        System.out.println("MCTS finished in " + (System.currentTimeMillis() - startTime) + "ms. Root stats: " + totalVisits + " visits.");
    }
    
    private Node select(Node startNode) {
        Node node = startNode;
        while (node.isFullyExpanded() && node.getNumChildren() > 0) {
            node = node.select(transpositionTable);
        }
        return node;
    }

    private double simulate(Node node) {
        StateObservation state = node.state.copy();
        for(int i=0; i<10; i++) { // Rollout depth
            if (state.isGameOver()) break;
            
            // Generic random rollout policy
            ArrayList<Types.ACTIONS> actions = state.getAvailableActions();
            if(actions.isEmpty()) break;
            Types.ACTIONS randomAction = actions.get(random.nextInt(actions.size()));
            state.advance(randomAction);
        }
        return getScore(state);
    }
    
    private double getScore(StateObservation state){
        if(state.getGameWinner() == Types.WINNER.PLAYER_WINS) return 1.0;
        if(state.getGameWinner() == Types.WINNER.PLAYER_LOSES) return -1.0;
        return 0.0;
    }

    private void outputResults(List<String> actions, boolean win, double score) {
        JSONObject json = new JSONObject();
        json.put("actions", actions);
        json.put("win", win);
        json.put("score", score);
        try (FileWriter file = new FileWriter("results.json")) {
            file.write(json.toJSONString());
            System.out.println("JSON results written to results.json");
        } catch (Exception e) {
            e.printStackTrace();
        }

        try (FileWriter file = new FileWriter("results.csv")) {
            file.write("actions,win,score\n");
            file.write(String.join(";", actions) + "," + win + "," + score + "\n");
            System.out.println("CSV results written to results.csv");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    private void shutdownExecutor() {
        if (!executor.isShutdown()) {

            try {
                if (!executor.awaitTermination(2, TimeUnit.SECONDS)) {
                    executor.shutdownNow();
                }
            } catch (InterruptedException e) {
                executor.shutdownNow();
            }
        }
    }
}
