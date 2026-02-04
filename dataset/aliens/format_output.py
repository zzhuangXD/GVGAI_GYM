import json
import sys
import os
from collections import deque

def format_json_output(input_file, output_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                print(f"Warning: {input_file} is empty.")
                return
            data = json.loads(content)

    except json.JSONDecodeError:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
                fixed_content = f"[{content.strip().replace('}{', '},{')}]"
                data = json.loads(fixed_content)[0]
        except (json.JSONDecodeError, IndexError) as e2:
            print(f"Failed to fix and decode JSON: {e2}")
            sys.exit(1)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('{\n')
        
        summary_str = json.dumps(data.get('summary', {}))
        f.write(f'  "summary": {summary_str},\n')

        dynamic_mapping_str = json.dumps(data.get('dynamic_mapping', {}))
        f.write(f'  "dynamic_mapping": {dynamic_mapping_str},\n')

        f.write('  "actions": [\n')
        actions = data.get('actions', [])
        symbol_mapping = data.get('dynamic_mapping', {})
        
        # Create a reverse mapping to easily find symbols
        alien_symbols = {symbol_mapping.get('alienGreen'), symbol_mapping.get('alienBlue')}
        alien_symbols.discard(None) # Remove None if a mapping doesn't exist
        avatar_symbol = symbol_mapping.get('avatar', 'A') # Default to 'A'
        sam_symbol = symbol_mapping.get('sam', 'S') # Default to 'S'

        previous_score = 0
        for i, action in enumerate(actions):
            f.write('    {\n')
            f.write(f'      "action_index": {action.get("action_index")},\n')
            f.write(f'      "action": "{action.get("action")}",\n')

            game_map = action.get('map', [])

            # Directly use the 'num_of_aliens' value from the original data
            num_of_aliens = action.get("num_of_aliens", 0)
            f.write(f'      "num_of_aliens": {num_of_aliens},\n')

            sam_exist = 1 if any(sam_symbol in row for row in game_map) else 0
            f.write(f'      "sam_present": {sam_exist},\n')
            
            # Find avatar position
            avatar_pos = None
            # First, search for the avatar symbol
            for y, row in enumerate(game_map):
                if avatar_symbol in row:
                    try:
                        x = row.index(avatar_symbol)
                        avatar_pos = [y, x]
                        break
                    except ValueError:
                        continue
            
            # If avatar not found, it might be covered by SAM; search for SAM symbol
            if avatar_pos is None:
                for y, row in enumerate(game_map):
                    if sam_symbol in row:
                        try:
                            x = row.index(sam_symbol)
                            avatar_pos = [y, x]
                            break
                        except ValueError:
                            continue

            f.write(f'      "avatar_position": {json.dumps(avatar_pos)},\n')

            current_score = action.get("score", 0)
            
            # Calculate score_change
            if i == 0:
                score_change = 0
            else:
                score_change = current_score - previous_score
            
            f.write(f'      "score": {current_score},\n')
            f.write(f'      "score_change": {score_change},\n')

            # Update previous_score for the next iteration
            previous_score = current_score

            f.write('      "map": [\n')
            
            # Directly iterate over the original game_map without transposing
            for j, row in enumerate(game_map):
                row_str = json.dumps(row)
                f.write(f'        {row_str}')
                if j < len(game_map) - 1:
                    f.write(',')
                f.write('\n')
            
            f.write('      ]\n')
            f.write('    }')
            if i < len(actions) - 1:
                f.write(',')
            f.write('\n')

        f.write('  ]\n')
        f.write('}\n')

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file_path = os.path.join(script_dir, 'output_L4.txt')

    format_json_output(output_file_path, output_file_path)
