
<div align="center">
  <h1 align="center">NoCode-bench: A Benchmark for Evaluating Natural
Language-Driven Feature Addition</h1>
</div>

<div align="center">
    <a href="https://github.com/ZJU-CTAG/NoCode-bench">
        <img src="https://img.shields.io/badge/GitHub-000?logo=github&logoColor=FFE165&style=for-the-badge" alt="">
    </a>
    <a href="https://huggingface.co/NoCode-bench">
        <img src="https://img.shields.io/badge/Datasets-000?logo=huggingface&logoColor=FFE165&style=for-the-badge" alt="">
    </a>
    <a href="https://arxiv.org/pdf/2507.18130">
        <img src="https://img.shields.io/badge/Paper-000?logoColor=FFE165&logo=arxiv&style=for-the-badge" alt="">
    </a>
    <a href="https://nocodebench.org/">
        <img src="https://img.shields.io/badge/Leaderboard-000?logoColor=FFE165&logo=googledocs&style=for-the-badge" alt="">
    </a>
    <a href="https://hub.docker.com/repository/docker/nocodebench/nocode-bench/">
        <img src="https://img.shields.io/badge/DockerHub-000?logoColor=FFE165&logo=docker&style=for-the-badge" alt="">
    </a>
    <hr>
</div>

## 📰 News
- **[2025-07-29]**: NoCode-bench is now available on Hugging Face Datasets! You can access it [here](https://huggingface.co/datasets/NoCode-bench).
- **[2025-07-18]**: We have released NoCode-bench, evaluate your SE Agent [here](https://arxiv.org/pdf/2507.18130).


## 📦 Benchmark Overview

**NoCode-bench** is a benchmark designed to evaluate the ability of Large Language Models (LLMs) to perform **no-code feature addition** using natural language documentation as input. Unlike prior benchmarks that focus on bug fixing or general issue resolution, NoCode-bench targets a new paradigm where feature development is driven by documentation changes in real-world software projects.

![task](./doc/task.png)

- **Instances**: 634 real-world feature addition tasks across diverse GitHub projects
- **Format**: Each instance contains the documentation change, relevant context files, and a ground truth patch
- **Subset**: Includes a manually verified subset (**NoCode-bench-Verified**) for high-quality, human-evaluated evaluation

[//]: # (> [!NOTE])

[//]: # (> We will provide the benchmark's Docker images and upload the benchmark to open-source platforms like huggingface after the paper can be de-anonymized.)

To access NoCode-bench, copy and run the following code:
```shell
from datasets import load_dataset
ncbench = load_dataset('NoCode-bench/NoCode-bench_Full', split='test')
ncbench_verified = load_dataset('NoCode-bench/NoCode-bench_Verified', split='test')
```

## 🚀 How to Use the Benchmark

### Environment Setup
Follow these steps to set up the environment for NoCode-bench:
```shell
conda create -n ncb python=3.12
conda activate ncb
pip install -r requirements.txt
```

NoCode-bench enables reproducible evaluations via Docker, by building the base image (`fb_base:dev`) and the project image (`fb_[repo]:dev`) as follows:

```bash
cd environment
bash setup_all.sh
```

We have also provided a pre-built Docker image for NoCode-bench, which can be pulled from Docker Hub:

```bash
cd environment
bash pull_from_hub.sh
```

[//]: # (### 2. Data Loading)

[//]: # ()
[//]: # (The benchmark data is stored in `data/instances/`:)

[//]: # ()
[//]: # (```sh)

[//]: # (results/)

[//]: # (  augmentation/)

[//]: # (    ├── ncb-verified_v0.1_augmented_masked.jsonl # FULL)

[//]: # (    └── ncb-verified_v0.1_augmented_masked.jsonl # VERUFIED)

[//]: # (```)

[//]: # ()
[//]: # (Each instance in `NoCode-bench-Verified` has been manually annotated to ensure **task clarity** and **evaluation accuracy**.)

[//]: # ()
[//]: # (### 3. Patch Generation)

[//]: # ()
[//]: # (First, load the data：)

[//]: # ()
[//]: # (```python)

[//]: # (bench_fpath = 'results/augmentation/fb-verified_v0.1_masked_augmented.jsonl')

[//]: # (instances = load_jsonl&#40;bench_fpath&#41;)

[//]: # (```)

[//]: # (For evaluation, you only need to focus on the following information)

[//]: # ()
[//]: # (Given an instance:)

[//]: # ()
[//]: # (- instance['instance_id']: unique identifier of the instance)

[//]: # (- instance['mask_doc_changes']: main input for the task)

[//]: # (- instance['augmentations']: optional input, which annotates newly introduced but undocumented entities to help mitigate FalseNegative caused by naming issues)


### Evaluation

You need to generate the prediction results that meet the following format for easy evaluation

```python
# Output Format
instances = [
  {
    'model_name_or_path': '...',
    'instance_id': '...',
    'model_patch': '...',
  },
  ...
]
```

Evaluate patch predictions on NoCode-bench Verified with the following command:

```sh
export PYTHONPATH=$PYTHONPATH:$(pwd)
python ./evaluation/eval.py \
    --predictions_path ./all_preds.jsonl \  # <path_to_your_predictions>
    --log_dir ./evaluation/logs \ # <path_to_your_log_dir>
    --feature_bench_tasks NoCode-bench/NoCode-bench_Verified \ # <dataset_name>
    --max_workers 110 \ # <number_of_workers>
    --output_file eval_result.txt \ # <path_to_your_output_file>
    --timeout 600 \ # <timeout_in_seconds>
    --proxy None # <proxy_if_needed>
```

------

## 🔧 How to Reconstruct the Benchmark

You can reproduce or extend NoCode-bench using our 5-step construction pipeline:

![workflow](./doc/workflow.png)

### Step 1: Project Selection

- Select high-quality, actively maintained GitHub repositories

```sh
cd repos/
sh collect.sh
```

### Step 2: Instance Collection

- Parse release notes to identify real feature addition tasks
- Retrieve corresponding PR from GitHub

```shell
python construction/collection/collect_[repo].py
python construction/filter_attribute/attribute_filter.py
```

### Step 3: Environment Construction

- All involved data and scripts are stored in the `environment/` folder
- Include related modules, configuration, and dependencies

### Step 4: Instance Filtering

- Automatically filter out instances that cannot meet our criteria

```shell
python construction/filter_execution/execution.py
```

### Step 5: Input Refinement

- Supplement missing but essential entity names in the task input.
- Mask information that may cause data leakage

```shell
python construction/augmentation/augment.py
python construction/augmentation/mask_auto.py
```

