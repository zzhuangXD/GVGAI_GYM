package tracks.singlePlayer.optimized_mcts;

import java.util.ArrayList;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;
import core.game.StateObservation;
import ontology.Types;
import tracks.singlePlayer.optimized_mcts.OptimizedMCTS.StateValue;

/**
 * Represents a node in the Monte Carlo Search Tree.
 * The value of this node (visits, score) is managed by an external transposition table.
 */
public class Node {
    private static final double UCT_K = Math.sqrt(2);
    private static Random random = new Random();

    public StateObservation state;
    public Node parent;
    public ArrayList<Node> children;
    public Types.ACTIONS action; // The action that led to this node

    private ArrayList<Types.ACTIONS> unexpandedActions;

    public Node(StateObservation state, Node parent, Types.ACTIONS action) {
        this.state = state;
        this.parent = parent;
        this.action = action;
        this.children = new ArrayList<>();
        this.unexpandedActions = state.getAvailableActions();
    }

    /**
     * Selects the best child node using the UCT algorithm, with values from the transposition table.
     */
    public Node select(ConcurrentHashMap<Long, StateValue> TTable) {
        Node selected = null;
        double bestValue = -Double.MAX_VALUE;

        StateValue parentStats = TTable.computeIfAbsent((long) this.state.hashCode(), k -> new StateValue());

        for (Node child : this.children) {
            StateValue childStats = TTable.computeIfAbsent((long) child.state.hashCode(), k -> new StateValue());
            
            double uctValue;
            synchronized(childStats) {
                uctValue = childStats.tot_value / (childStats.n_visits + 1e-6);
            }
            synchronized(parentStats) {
                 uctValue += UCT_K * Math.sqrt(Math.log(parentStats.n_visits + 1) / (childStats.n_visits + 1e-6));
            }
            
            if (uctValue > bestValue) {
                selected = child;
                bestValue = uctValue;
            }
        }
        return selected;
    }

    /**
     * Expands the current node by creating a new child node.
     */
    public Node expand() {
        if (unexpandedActions.isEmpty()) {
            return null; // No more actions to expand
        }

        Types.ACTIONS newAction = unexpandedActions.remove(random.nextInt(unexpandedActions.size()));
        StateObservation nextState = state.copy();
        nextState.advance(newAction);

        Node newNode = new Node(nextState, this, newAction);
        children.add(newNode);
        return newNode;
    }

    /**
     * Backpropagates the result, updating values in the transposition table up from the current node.
     */
    public void backpropagate(double value, ConcurrentHashMap<Long, StateValue> TTable) {
        Node current = this;
        while (current != null) {
            StateValue stats = TTable.computeIfAbsent((long) current.state.hashCode(), k -> new StateValue());
            stats.update(value);
            current = current.parent;
        }
    }

    public boolean isFullyExpanded() {
        return unexpandedActions.isEmpty();
    }

    public int getNumChildren() {
        return children.size();
    }
}
