# Prompts for running Agentless on NoCode-bench

---

## Overview

This folder contains the moditfied prompts for running Agentless on NoCode-bench. 
```text
agentless_localization_prompt.py # Prompt for localization stage
agentless_repair_prompt.py # Prompt for repair stage
```

## How to run Agentless on NoCode-bench
First, you should replace the original prompts in `agentless/fl/FL.py` and `agentless/repair/repair.py` with the modified prompts in this folder. 

Then, you can run Agentless on NoCode-bench following original instruction of Agentless evaluated on SWE-bench [here](https://github.com/OpenAutoCoder/Agentless/blob/main/README_swebench.md).

> [!NOTE]
> We do not use the validation stage in Agentless, so you can skip the reproduction stage when running Agentless on NoCode-bench.
