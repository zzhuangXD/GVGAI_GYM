# Zelda_README

* 输出文件与相关代码路径：GVGAI_GYM\dataset\zelda

* 示例输出：GVGAI_GYM\dataset\zelda\Example

0. 在项目根目录下```conda env create -f environment.yml```重建环境

1. 修改run2.sh中LAUNCHING AGENT ON...部分的参数，更改为当前想要运行的游戏X和level Y
   ```
   java -cp $RUNTIME_CP core.competition.AgentExecutor gym_gvgai/envs/games/X_v0/X.txt gym_gvgai/envs/games/X_v0/X_lvlY.txt tracks.singlePlayer.optimized_mcts.OptimizedMCTS ./dataset/X/output.txt
   ```
   运行run2.sh, 输出**output.txt**，包含每一个action的基本数据, 命令为

   ```
   ./run2.sh
   ```

2. **output.txt** -> **output_formatted.txt**, 基于map中的内容，逐action添加统计信息，并且重整格式

   ```
   python ./dataset/zelda/format_output.py
   ```

3. **output_formatted.txt** -> **valid_actions.txt**, 抽除没有对状态产生实际影响的action

   ```
   python ./dataset/zelda/extract_valid_actions.py
   ```

4. **valid_actions.txt** -> **zelda_dataset.json**, 将数据提取为自然语言信息生成input-output pairs

   ```
   python ./dataset/zelda/actions_to_IOpairs.py
   ```

5. **zelda_dataset.json** -> **zelda_dataset_readable.txt**，将pairs处理为显式换行的，易读的文本形式

   ```
   python ./dataset/zelda/json_to_human_read.py
   ```

