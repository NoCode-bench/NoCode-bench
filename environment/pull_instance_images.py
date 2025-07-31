#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import docker
from tqdm import tqdm
from datasets import load_dataset


DOCKERHUB_USER = 'nocodebench'
REPO_NAME = 'nocode-bench-instances'


def pull_and_tag_image(client, instance_id):
    remote_tag = f'{DOCKERHUB_USER}/{REPO_NAME}:ncbench_{instance_id}'
    local_tag = f'ncbench_{instance_id}:latest'

    try:
        print(f'Pulling {remote_tag} ...')
        image = client.images.pull(remote_tag)
        image.tag(local_tag)
        print(f'Tagged as {local_tag}')
        return True
    except Exception as e:
        print(f'Failed to pull/tag {remote_tag}: {e}')
        return False


def main():
    parser = argparse.ArgumentParser(description='Pull and rename ncbench images from Docker Hub')
    parser.add_argument("--bench_tasks", type=str, help="Path to benchmark task instances file", required=True,
                        choices=['NoCode-bench/NoCode-bench_Verified', 'NoCode-bench/NoCode-bench_Full'], default='NoCode-bench/NoCode-bench_Verified')
    args = parser.parse_args()

    tasks = load_dataset(args.bench_tasks, split='test')
    client = docker.from_env()

    for task in tqdm(tasks, desc='pulling'):
        instance_id = task['instance_id']
        pull_and_tag_image(client, instance_id)


if __name__ == '__main__':
    main()
