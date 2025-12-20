import json
import os

def check_char_in_map(game_map, char_to_find):
    """Checks if a character exists in the game map."""
    if not game_map:
        return False
    for row in game_map:
        if char_to_find in row:
            return True
    return False

def write_sequences_pretty(data_object, filename):
    """
    Writes the final data object to a file with custom pretty-printing.
    The object is expected to have 'summary', 'dynamic_mapping', and 'sequences'.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        summary = data_object.get("summary", {})
        dynamic_mapping = data_object.get("dynamic_mapping", {})
        sequences = data_object.get("sequences", [])

        f.write('{\n')
        f.write(f'  "summary": {json.dumps(summary)},\n')
        f.write(f'  "dynamic_mapping": {json.dumps(dynamic_mapping)},\n')
        
        f.write('  "sequences": [\n')
        if sequences:
            for i, block in enumerate(sequences):
                f.write("    {\n")
                
                f.write(f'      "sequence_index": {block["sequence_index"]},\n')
                f.write(f'      "score_change": {block["score_change"]},\n')
                f.write(f'      "base_destroyed": {block["base_destroyed"]},\n')
                f.write(f'      "alien_eliminated": {block["alien_eliminated"]},\n')
                f.write(f'      "init_num_of_aliens": {block.get("init_num_of_aliens", "null")},\n')
                f.write(f'      "end_num_of_aliens": {block.get("end_num_of_aliens", "null")},\n')
                f.write(f'      "init_avatar_pos": {json.dumps(block.get("init_avatar_pos"))},\n')
                f.write(f'      "end_avatar_pos": {json.dumps(block.get("end_avatar_pos"))},\n')
                f.write(f'      "action_indices": {json.dumps(block["action_indices"])},\n')
                f.write(f'      "action_sequence": {json.dumps(block["action_sequence"])},\n')

                f.write('      "initial_map": [\n')
                for j, row in enumerate(block["initial_map"]):
                    f.write(f'        {json.dumps(row)}')
                    if j < len(block["initial_map"]) - 1:
                        f.write(',')
                    f.write('\n')
                f.write('      ],\n')

                f.write('      "end_map": [\n')
                for j, row in enumerate(block["end_map"]):
                    f.write(f'        {json.dumps(row)}')
                    if j < len(block["end_map"]) - 1:
                        f.write(',')
                    f.write('\n')
                f.write('      ]\n')

                f.write("    }")
                if i < len(sequences) - 1:
                    f.write(",\n")
                else:
                    f.write("\n")
        
        f.write('  ]\n')
        f.write('}\n')


def find_action_sequences(input_file, output_file):
    """
    Reads game trajectory, extracts sequences, and wraps them with summary info.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing {input_file}: {e}")
        return

    summary = data.get("summary", {})
    dynamic_mapping = data.get("dynamic_mapping", {})
    actions = data.get("actions", [])
    
    if not actions:
        print("No 'actions' found in the input file.")
        # Write empty structure if no actions
        write_sequences_pretty({"summary": summary, "dynamic_mapping": dynamic_mapping, "sequences": []}, output_file)
        return

    # --- Phase 1: Map all scoring events to their launch points ---
    launch_to_scores = {}
    for i, action in enumerate(actions):
        current_score_change = action.get("score_change", 0)
        if current_score_change > 0:
            score_point_X = i
            
            launch_point_Y = -1
            for j in range(score_point_X - 1, -1, -1):
                if j + 1 >= len(actions):
                    continue
                
                cond1 = actions[j].get("action") == "ACTION_USE"
                cond2 = actions[j].get("sam_present", 0) == 0
                cond3 = actions[j+1].get("sam_present", 0) == 1
                map_at_Y_plus_1 = actions[j+1].get("map", [])
                cond4 = not check_char_in_map(map_at_Y_plus_1, 'A')

                if cond1 and cond2 and cond3 and cond4:
                    launch_point_Y = j
                    break
            
            if launch_point_Y != -1:
                if launch_point_Y not in launch_to_scores:
                    launch_to_scores[launch_point_Y] = {'scores': [], 'base_destroyed': 0, 'alien_eliminated': 0}
                
                launch_to_scores[launch_point_Y]['scores'].append(current_score_change)
                if current_score_change == 1.0:
                    launch_to_scores[launch_point_Y]['base_destroyed'] += 1
                elif current_score_change == 2.0:
                    launch_to_scores[launch_point_Y]['alien_eliminated'] += 1

    # --- Phase 2: Build final sequences from the map ---
    blocks = []
    sequence_index_counter = 1
    last_sequence_end_index = -1
    
    sorted_launch_points = sorted(launch_to_scores.keys())

    for launch_point_Y in sorted_launch_points:
        default_start_index = max(0, launch_point_Y - 9)
        non_overlapping_start_index = max(default_start_index, last_sequence_end_index + 1)
        end_index = launch_point_Y

        if non_overlapping_start_index <= end_index:
            action_indices = [
                actions[j].get("action_index") 
                for j in range(non_overlapping_start_index, end_index + 1)
            ]
            action_sequences = [
                actions[j].get("action")
                for j in range(non_overlapping_start_index, end_index + 1)
            ]

            if action_indices:
                score_info = launch_to_scores[launch_point_Y]
                
                block = {
                    "sequence_index": sequence_index_counter,
                    "score_change": sum(score_info['scores']),
                    "base_destroyed": score_info['base_destroyed'],
                    "alien_eliminated": score_info['alien_eliminated'],
                    "init_num_of_aliens": actions[non_overlapping_start_index].get("num_of_aliens"),
                    "end_num_of_aliens": actions[end_index].get("num_of_aliens"),
                    "init_avatar_pos": actions[non_overlapping_start_index].get("avatar_position"),
                    "end_avatar_pos": actions[end_index].get("avatar_position"),
                    "action_indices": action_indices,
                    "action_sequence": action_sequences,
                    "initial_map": actions[non_overlapping_start_index].get("map"),
                    "end_map": actions[end_index].get("map")
                }
                blocks.append(block)
                sequence_index_counter += 1
            
            last_sequence_end_index = end_index

    final_output = {
        "summary": summary,
        "dynamic_mapping": dynamic_mapping,
        "sequences": blocks
    }

    write_sequences_pretty(final_output, output_file)
    print(f"Successfully extracted {len(blocks)} sequences and wrapped in final structure to {output_file}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file_path = os.path.join(script_dir, 'output.txt')
    output_file_path = os.path.join(script_dir, 'action_sequences.json')
    
    find_action_sequences(input_file_path, output_file_path)
