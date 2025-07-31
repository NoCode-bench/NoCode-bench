#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import docker
from tqdm import tqdm
from datasets import load_dataset

DOCKERHUB_USER = 'nocodebench'
REPO_NAME = 'nocode-bench-instances'


def docker_login(client, username: str, password: str):
    try:
        client.login(username=username, password=password)
        print(f'Successfully logged in as {username}')
    except docker.errors.APIError as e:
        print(f'Login failed: {e}')
        exit(1)


def push_image(client, instance_id):
    local_tag = f'ncbench_{instance_id}:latest'
    remote_tag = f'{DOCKERHUB_USER}/{REPO_NAME}:ncbench_{instance_id}'

    try:
        image = client.images.get(local_tag)
        image.tag(remote_tag)
        print(f'Tagged {local_tag} as {remote_tag}')
        for line in client.images.push(remote_tag, stream=True, decode=True):
            status = line.get('status') or line.get('error')
            if status:
                print(status)
        return True
    except Exception as e:
        print(f'Failed to push image {local_tag}: {e}')
        return False


def main():
    parser = argparse.ArgumentParser(description='Push ncbench images to a specific Docker Hub repository')
    parser.add_argument("--bench_tasks", type=str, help="Path to benchmark task instances file", required=True,
                        choices=['NoCode-bench/NoCode-bench_Verified', 'NoCode-bench/NoCode-bench_Full'],
                        default='NoCode-bench/NoCode-bench_Verified')
    parser.add_argument('--dockerhub_user', required=True,
                        help='Docker Hub username')
    parser.add_argument('--dockerhub_pass', required=False,
                        help='Docker Hub password (or use DOCKERHUB_PASS env var)')
    args = parser.parse_args()

    password = args.dockerhub_pass or os.getenv('DOCKERHUB_PASS')
    if not password:
        print('Docker Hub password not provided (use --dockerhub_pass or DOCKERHUB_PASS env var)')
        exit(1)

    tasks = load_dataset(args.bench_tasks, split='test')
    client = docker.from_env()

    docker_login(client, args.dockerhub_user, password)

    for task in tqdm(tasks, desc='pushing'):
        instance_id = task['instance_id']
        push_image(client, instance_id)


if __name__ == '__main__':
    main()
