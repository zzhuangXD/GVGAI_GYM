# escape_README

* 输出文件与相关代码路径：GVGAI_GYM\dataset\escape

* 示例输出：GVGAI_GYM\dataset\escape\Example


0. 在项目根目录下```conda env create -f environment.yml```重建环境

1. 修改run2.sh中LAUNCHING AGENT ON...部分的参数，更改为当前想要运行的游戏X和level Y
   ```
   java -cp $RUNTIME_CP core.competition.AgentExecutor gym_gvgai/envs/games/X_v0/X.txt gym_gvgai/envs/games/X_v0/X_lvlY.txt tracks.singlePlayer.optimized_mcts.OptimizedMCTS ./dataset/X/output.txt
   ```
   运行run2.sh, 输出**output.txt**，包含每一个action的基本数据, 命令为

   ```
   ./run2.sh
   ```

2. **output.txt** -> **output.txt**，逐action添加统计信息（如当前map中num_of_aliens, 与上一帧相比score_change等）

   ```
   python ./dataset/escape/format_output.py
   ```

3. **output.txt** -> **action_sequences.json**，actions被合并为sequence

   ```
   python ./dataset/aliens/action_to_sequences.py
   ```

4. **action_sequences.json** -> **aliens_dataset.json**，将sequences处理为input-output pairs

   ```
   python ./dataset/aliens/sequences_to_IOpairs.py
   ```

5. **action_sequences.json** -> **aliens_dataset_readable.txt**，将pairs处理为显式换行的，易读的文本形式

   ```
   python ./dataset/aliens/json_to_human_read.py
   ```

# Tips

1. Player.java Line 193被注释的code section举例了如何用built-in的函数计算一类NPC对象的个数

   ArrayList<Observation>[] npcPositions = turn.state.getNPCPositions(); 

   该数组中的每一项是对应于一个NPC的ArrayList，该ArrayList包含当前游戏状态下，该类NPC的每一个对象的Observation：

   --- Debugging action_index: 286 ---
   npcPositions array length: 1
   List 0 (itype: 9): contains 11 objects.
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=380, position=450.0 : 100.0, reference=-1.0 : -1.0, sqDist=213602.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=382, position=325.0 : 100.0, reference=-1.0 : -1.0, sqDist=116477.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=387, position=50.0 : 100.0, reference=-1.0 : -1.0, sqDist=12802.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=390, position=50.0 : 50.0, reference=-1.0 : -1.0, sqDist=5202.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=405, position=850.0 : 50.0, reference=-1.0 : -1.0, sqDist=726802.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=408, position=900.0 : 0.0, reference=-1.0 : -1.0, sqDist=811802.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=415, position=625.0 : 0.0, reference=-1.0 : -1.0, sqDist=391877.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=417, position=500.0 : 0.0, reference=-1.0 : -1.0, sqDist=251002.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=421, position=350.0 : 0.0, reference=-1.0 : -1.0, sqDist=123202.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=425, position=225.0 : 0.0, reference=-1.0 : -1.0, sqDist=51077.0}
    -> Observation{category=3, itype=9, itypeKey=alienBlue, obsID=429, position=100.0 : 0.0, reference=-1.0 : -1.0, sqDist=10202.0}

   ------------------------------

   以上为npcPositions的第一项，即ArrayList 0，其内每个Observation均为同一类NPC(itype=9, itypeKey=)的不同实例，该ArrayList包含11个Observation即该类NPC有11个对象

2. 手动PlayOneGame

   ```
   ./run1.sh
   ```