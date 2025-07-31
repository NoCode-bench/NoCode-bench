#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
create_instance_image.py

Build a minimal ncbench_{instance_id}:latest image for each SWE-bench instance.
Steps: checkout base commit → run pre_install → install deps → commit image.
No patches and no tests are applied.
"""

import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import docker
from tqdm import tqdm

import utils.docker_utils as du
from construction.filter_execution.constants import MAP_REPO_TO_CONFIG
from utils.logger import get_logger
from datasets import load_dataset


def build_image_for_instance(task: dict,
                             client: docker.DockerClient,
                             log_dir: str,
                             proxy: str = None):
    instance_id = task['instance_id']
    repo_url    = task['repo']
    repo_name   = repo_url.split('/')[-1]
    work_dir    = f'/root/{repo_name}'

    logger = get_logger(instance_id,
                        os.path.join(log_dir, f'{instance_id}.log'))
    container = None
    try:
        # 1. 启动容器
        container = du.build_container(
            image_name=f'fb_{repo_name}:dev',
            container_name=f'fb_{repo_name}__{instance_id}',
            client=client,
            logger=logger,
            proxy=proxy
        )
        container.start()

        # 2. 清理并切换到 base_commit
        container.exec_run('git clean -fdx', workdir=work_dir)
        container.exec_run('git reset --hard HEAD', workdir=work_dir)
        container.exec_run(f'git checkout {task["base_commit"]}', workdir=work_dir)

        # 3. 预安装脚本和依赖安装
        cfg = MAP_REPO_TO_CONFIG[repo_url][task['version']]
        for cmd in cfg.get('pre_install', []):
            container.exec_run(cmd, workdir=work_dir, demux=True)
        install_cmd = f'conda run -n {cfg["conda_env"]} {cfg["install"]}'
        container.exec_run(install_cmd, workdir=work_dir, demux=True)

        # 4. 提交镜像
        img_repo, img_tag = f'ncbench_{instance_id}', 'latest'
        if not any(img_repo in tag
                   for img in client.images.list(name=img_repo)
                   for tag in img.tags):
            img = container.commit(repository=img_repo, tag=img_tag)
            logger.info(f'committed image: {img.tags[0]}')

    except Exception as e:
        logger.error(f'build failed: {e}')
    finally:
        du.cleanup_container(client, container, logger)


def main():
    parser = argparse.ArgumentParser(
        description='Build ncbench images from SWE-bench tasks (no patches, no tests)')
    parser.add_argument("--bench_tasks", type=str, help="Path to benchmark task instances file", required=True,
                        choices=['NoCode-bench/NoCode-bench_Verified', 'NoCode-bench/NoCode-bench_Full'],
                        default='NoCode-bench/NoCode-bench_Verified')
    parser.add_argument('--log_dir', required=True,
                        help='Directory for build logs')
    parser.add_argument('--max_workers', type=int, default=1,
                        help='Thread pool size')
    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    logger = get_logger('build_images',
                        os.path.join(args.log_dir, 'build_images.log'))
    logger.info(args)

    tasks = load_dataset(args.bench_tasks, split='test')
    client = docker.from_env()

    if args.max_workers == 1:
        for t in tqdm(tasks, desc='building'):
            build_image_for_instance(t, client, args.log_dir)
    else:
        with ThreadPoolExecutor(args.max_workers) as pool:
            futures = [pool.submit(build_image_for_instance,
                                   t, client, args.log_dir) for t in tasks]
            for _ in tqdm(as_completed(futures),
                          total=len(futures), desc='building'):
                pass

    logger.info('all done')


if __name__ == '__main__':
    main()
