import collections
from concurrent.futures import ThreadPoolExecutor, as_completed
import difflib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import re
from threading import Lock
from packaging.version import parse
import docker
from tqdm import tqdm
from unidiff import PatchSet

# # 获取当前脚本所在的目录，并向上导航到父目录
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)

# # 将父目录添加到sys.path
# if parent_dir not in sys.path:
#     sys.path.append(parent_dir)
    
from utils.logger import get_logger
from utils.utils import load_jsonl, PatchTools, dump_jsonl, run_cmd, run_cmd_with_err
from utils.github import get_pr_info
import utils.docker_utils as du
from filter_execution.constants import *
from construction.filter_execution.testlog_extractor import *
    
client  = docker.from_env()


class SympyExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/sympy'
        self.attr_fpath = 'cache/attribute/sympy_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_sympy'
        self.work_dir='/root/sympy'
    
    def run(self):
        self.preprocess()
        self.test_filter(max_workers=1)
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_set = set()
        version_patterns = [r'__version__ = [\'"](.*)[\'"]', r"VERSION = \((.*)\)"]
        version_file_list = ["sympy/release.py", "sympy/__init__.py"]
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            # 过滤feature_patch中包含其他语言的样例
            # get version
            cmd_res = ''
            for version_file in version_file_list:
                git_cmd = f'git show {base_commit}:{version_file}'
                cmd_res += run_cmd(git_cmd, self.repo_dir)
            for pattern in version_patterns:
                match = re.search(pattern, cmd_res)
                if match:
                    break
            version = match.group(1)
            version_set.add(version)
            version = '.'.join(version.split('.')[:2])
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                # if hunk['path'].startswith('doc/'):
                    doc_changes.append(hunk)
                elif 'tests/' in hunk['path']:
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
    
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()



class MatplotlibExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/matplotlib'
        self.attr_fpath = 'cache/attribute/matplotlib_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_matplotlib'
        self.work_dir='/root/matplotlib'
    
    def run(self):
        self.preprocess()
        self.test_filter(max_workers=16)
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_pattern = r"^github_stats_(.+)\.rst$"
        version_set = set()
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            run_cmd(f'git checkout {base_commit}', cwd=self.repo_dir)
            version_doc_path = os.path.join(self.repo_dir, 'doc/users/prev_whats_new')
            if os.path.exists(version_doc_path):
                file_list = os.listdir(version_doc_path)
                # 过滤feature_patch中包含其他语言的样例
                # get version
                versions = []
                for i in file_list:
                    match = re.match(version_pattern, i)
                    if match:
                        version_str = match.group(1)
                        versions.append(parse(version_str))
                if not versions:
                    continue
                latest_version = max(versions)
                version = '.'.join(str(latest_version).split('.')[:2])
            else:
                version_pattern = r"tag:\s*v(\d+\.\d+\.\d+)"
                file_content = open('repos/matplotlib/doc/users/github_stats.rst').read()
                match = re.search(version_pattern, file_content)
                if match:
                    version = '.'.join(match.group(1).split('.')[:2])
                # 获取
            version_set.add(version)
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif any(i in hunk['path'] for i in ['tests/', 'testing']):
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
    
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()



class RequestsExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/requests'
        self.attr_fpath = 'cache/attribute/requests_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_requests'
        self.work_dir='/root/requests'
    
    def run(self):
        self.preprocess()
        self.test_filter(max_workers=1)
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_set = set()
        version_patterns = [r'__version__ = [\'"](.*)[\'"]', r"VERSION = \((.*)\)"]
        version_file_list = ["requests/__version__.py", "requests/__init__.py"]
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            # 过滤feature_patch中包含其他语言的样例
            # get version
            cmd_res = ''
            for version_file in version_file_list:
                git_cmd = f'git show {base_commit}:{version_file}'
                cmd_res += run_cmd(git_cmd, self.repo_dir)
            for pattern in version_patterns:
                match = re.search(pattern, cmd_res)
                if match:
                    break
            version = match.group(1)
            version_set.add(version)
            version = '.'.join(version.split('.')[:2])
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif 'tests/' in hunk['path']:
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
    
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()


class PytestExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/pytest'
        self.attr_fpath = 'cache/attribute/pytest_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_pytest'
        self.work_dir='/root/pytest'
    
    def run(self):
        self.preprocess()
        self.test_filter(max_workers=1)
    
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            # pytest只能使用testing
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'], test_words=['testing'])
            # 过滤feature_patch中包含其他语言的样例
            # get version
            version = example['metadata']['update_info']['version'][7:10]
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif 'testing/' in hunk['path']:
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
    
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()


class PylintExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/pylint'
        self.attr_fpath = 'cache/attribute/pylint_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_pylint'
        self.work_dir='/root/pylint'
    
    def run(self):
        self.preprocess()
        # self.test_filter(max_workers=1)
    
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_patterns = [r'__version__ = [\'"](.*)[\'"]', r"VERSION = \((.*)\)"]
        version_file_list = ["pylint/__pkginfo__.py", "pylint/__init__.py"]
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            # 过滤feature_patch中包含其他语言的样例
            # get version
            cmd_res = ''
            for version_file in version_file_list:
                git_cmd = f'git show {base_commit}:{version_file}'
                cmd_res += run_cmd(git_cmd, self.repo_dir)
            for pattern in version_patterns:
                match = re.search(pattern, cmd_res)
                if match:
                    break
            version = match.group(1)
            version = '.'.join(version.split('.')[:2])
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif 'tests/' in hunk['path']:
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()


class DjangoExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/django'
        self.attr_fpath = 'cache/attribute/django_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_django'
        self.work_dir='/root/django'
    
    def run(self):
        self.preprocess()
        self.test_filter(max_workers=32)
    
    def _get_doc_and_test(self, diff_content):
        doc_list = []
        test_lists = [] # 去除前面的tests/ 和结尾的.py 所有的/替换成.
        diff_hunks = PatchTools.get_diff_hunks(diff_content)
        for hunk in diff_hunks:
            fpath = hunk['new_path']
            if 'test' in fpath and fpath.endswith('.py'):
                test_lists.append(fpath[2:])
            elif any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                doc_list.append(hunk)
        test_need_to_run = []
        for test in test_lists:
            new_test = test.removeprefix('tests/')
            new_test = new_test.removesuffix('.py')
            new_test = new_test.replace('/', '.')
            test_need_to_run.append(new_test)
        
        return doc_list, test_need_to_run
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_pattern = r'stable/(\d+\.\d+)'
        pyversion_pattern = r'\d+\.\d+'
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            version = example['metadata']['branch']
            base_commit = example['pr_info']['base']['sha']
            # 某些commit_hash不属于该仓库
            match = re.search(version_pattern, version)
            if not match:
                continue
            version = match.group(1)
            git_cmd = f'git show {base_commit}:INSTALL'
            cmd_res = run_cmd(git_cmd, self.repo_dir)
            # get INSTALL file
            match = re.search(pyversion_pattern, cmd_res)
            py_version = match.group()
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            # get doc changes
            doc_changes, tests = self._get_doc_and_test(example['diff_info'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
    
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()


class SeabornExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/seaborn'
        self.attr_fpath = 'cache/attribute/seaborn_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_seaborn'
        self.work_dir='/root/seaborn'
    
    def extract_doc_update(self, example):
        diff_info = example['diff_info']
        hunks = PatchTools.get_diff_hunks(diff_info)
        # 获得ipynb的更新
        doc_hunks = []
        for hunk in hunks:
            hunk_path = hunk['path']
            if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                doc_hunks.append(hunk)
        return doc_hunks

    def process_ipynb_changes(self, example):
        # 获得所有ipynb的hunk
        doc_changes = example['doc_changes']
        processed_changes = []
        ipynb_changes = []
        for change in doc_changes:
            if change['path'].endswith('.ipynb'):
                ipynb_changes.append(change)
            else:
                change['update'] = change['metadata']
                processed_changes.append(change)
        if ipynb_changes:
            base_commit = example['execution']['base_commit']
            # reset branch
            run_cmd('git clean -fd', self.repo_dir)
            run_cmd('git reset --hard HEAD', self.repo_dir)
            # checkout base_commit 
            git_checkout_cmd = f'git checkout {base_commit}'
            git_checkout_res = run_cmd(git_checkout_cmd, self.repo_dir)
            # 前后：提取ipynb中的所有的sources
            for change in ipynb_changes:
                doc_content = ''
                if change['old_path'] != '/dev/null':
                    before_doc = open(os.path.join(self.repo_dir, change['old_path'][2:]), 'r', encoding='utf-8').read()
                    before_doc_json = json.loads(before_doc)
                    # print(before_doc)
                    doc_content = '\n'.join(['\n'.join(i['source']) for i in before_doc_json['cells']])
                change['old_content'] = doc_content
            # apply patch
            with open(TEMP_PATCH, 'w') as f:
                f.write(example['execution']['feature_patch'])
            apply_patch_cmd = f'git apply {TEMP_PATCH}'
            apply_patch_res = run_cmd(apply_patch_cmd, self.repo_dir, print_err=False)
            for change in ipynb_changes:
                doc_content = ''
                if change['new_path'] != '/dev/null':
                    after_doc = open(os.path.join(self.repo_dir, change['new_path'][2:]), 'r', encoding='utf-8').read()
                    after_doc_json = json.loads(after_doc)
                    # print(before_doc)
                    doc_content = '\n'.join(['\n'.join(i['source']) for i in after_doc_json['cells']])
                change['new_content'] = doc_content
            for change in ipynb_changes:
                a = change['old_content'].splitlines(True)
                b = change['new_content'].splitlines(True)
                diff = difflib.unified_diff(a, b, fromfile=change['old_path'], tofile=change['new_path'])
                diff_content = ''.join(diff)
                change['update'] = str(diff_content)
                change.pop('old_content')
                change.pop('new_content')
                processed_changes.append(change)
        return processed_changes

    
    def extract_doc(self):
        examples = load_jsonl(self.final_fpath)
        for example in examples:
            doc_hunks = self.extract_doc_update(example)
            example['doc_changes'] = doc_hunks
            example['execution']['doc_changes'] = self.process_ipynb_changes(example)
            del example['doc_changes']
        dump_jsonl(examples, self.final_fpath)
    
    def run(self):
        # self.preprocess()
        # self.test_filter(max_workers=5)
        self.extract_doc()
    
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_patterns = [r'__version__\s*=\s*[\'"](.*)[\'"]', r"VERSION\s*=\s*\((.*)\)"]
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            git_cmd = f'git show {base_commit}:seaborn/__init__.py'
            cmd_res = run_cmd(git_cmd, self.repo_dir)
            for pattern in version_patterns:
                match = re.search(pattern, cmd_res)
                if match:
                    break
            version = '.'.join(match.group(1).split('.')[:2])
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif 'tests/' in hunk['path'] and hunk['path'].endswith('.py'):
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
        
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()


class AstropyExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/astropy'
        self.attr_fpath = 'cache/attribute/astropy_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_astropy'
        self.work_dir='/root/astropy'
    
    def run(self):
        self.preprocess()
        self.test_filter(max_workers=32)
    
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_pattern = r'VERSION\s*=\s*[\'"]([^"]+)[\'"]'
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            # 过滤feature_patch中包含其他语言的样例
            
            # get version
            git_cmd = f'git show {base_commit}:setup.py'
            cmd_res = run_cmd(git_cmd, self.repo_dir)
            match = re.search(version_pattern, cmd_res)
            if match:
                version = match.group(1)
                version_parts = version.split('.')[:2]
                version = '.'.join(version_parts)
            else:
                version_info = example['metadata']['update_info']['version']
                pattern = r'Version (\d\.\d).+'
                version = re.search(pattern, version_info).group(1)
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif 'tests/' in hunk['path']:
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
    
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()


class XarrayExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/xarray'
        self.attr_fpath = 'cache/attribute/xarray_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_xarray'
        self.work_dir='/root/xarray'
    
    def run(self):
        self.preprocess()
        self.test_filter(max_workers=16)
    
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        id_set = set()
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            if example['instance_id'] in id_set:
                continue
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])

            version_info = example['metadata']['update_info']['version']
            for keyword in ['v.', 'v']:
                if version_info.startswith(keyword):
                    version_info = version_info[len(keyword):]
            version_info = version_info.split(' (')[0]
            if version_info.startswith('0.'):
                version = '0' + ''.join(version_info.split('.')[:2])
            elif version_info.startswith('202'):
                version = ''.join(version_info[2:].split('.')[:2])
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif 'tests/' in hunk['path']:
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
            id_set.add(example['instance_id'])
        dump_jsonl(res, out_fpath)
    
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()

             
class SKLearnExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/scikit-learn'
        self.attr_fpath = 'cache/attribute/scikit-learn_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_scikit-learn'
        self.work_dir='/root/scikit-learn'
    
    def run(self):
        self.preprocess()
        self.test_filter(max_workers=16)
    
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_pattern = r'__version__\s*=\s*[\'"]([^"]+)[\'"]'
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            
            git_cmd = f'git show {base_commit}:sklearn/__init__.py'
            cmd_res = run_cmd(git_cmd, self.repo_dir)
            match = re.search(version_pattern, cmd_res)
            version = match.group(1)
            version_parts = version.split('.')[:2]
            version_parts[1] = version_parts[1] if len(version_parts[1]) >1 else str('0' + version_parts[1])
            version = '.'.join(version_parts)
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif 'tests/' in hunk['path'] and hunk['path'].endswith('.py'):
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
        
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return 
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()

                        
class SphinxExeFilter:
    def __init__(self):
        self.repo_dir = 'repos/sphinx'
        self.attr_fpath = 'cache/attribute/sphinx_with_diff_filter.jsonl'
        repo_name = self.repo_dir.replace('repos/', '')
        self.root_dir = os.path.join('results', repo_name)
        os.makedirs(self.root_dir, exist_ok=True)
        self.log_dir = os.path.join(self.root_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.preprocess_fpath = os.path.join(self.root_dir, 'preprocess.jsonl')
        self.final_fpath = os.path.join(self.root_dir, 'examples.jsonl')
        self.image_name = 'fb_sphinx'
        self.work_dir='/root/sphinx'
    
    def run(self):
        self.preprocess()
        self.test_filter(16)
    
    
    def preprocess(self):
        out_fpath = self.preprocess_fpath
        if os.path.exists(out_fpath):
            return load_jsonl(out_fpath)
        examples = load_jsonl(self.attr_fpath)
        res = []
        version_patterns = [r'__version__\s*=\s*[\'"](.*)[\'"]', r"VERSION\s*=\s*\((.*)\)"]
        for example in tqdm(examples):
            example['instance_id'] = example['instance_id'].replace('/', '__')
            pr_id = example['instance_id'].split('-')[-1]
            pr_info = get_pr_info(example['repo'], pr_id)
            if pr_info is None:
                print(pr_id)
                continue
            base_commit = pr_info['base']['sha']
            feature_patch, test_patch = PatchTools.get_patches(example['diff_info'])
            git_cmd = f'git show {base_commit}:sphinx/__init__.py'
            cmd_res = run_cmd(git_cmd, self.repo_dir)
            for pattern in version_patterns:
                match = re.search(pattern, cmd_res)
                if match:
                    break
            if match:
                version = match.group(1)[:3]
            doc_changes = []
            tests = []
            for hunk in PatchTools.get_diff_hunks(example['diff_info']):
                if any(re.match(p, hunk['path']) for p in DOCPATH_PATTERNS):
                    doc_changes.append(hunk)
                elif 'tests/' in hunk['path']:
                    tests.append(hunk['path'])
            example['execution'] = {
                'feature_patch': feature_patch,
                'test_patch': test_patch,
                'tests': tests,
                'doc_changes': doc_changes,
                'version': version,
                'base_commit': base_commit
            }
            res.append(example)
        dump_jsonl(res, out_fpath)
    
    
    def process_example(self, example, existing=set(), write_lock=None):
        instance_id = example['instance_id']
        log_file = os.path.join(self.log_dir, f'{instance_id}.log')
        logger = get_logger(log_name=log_file, log_file=log_file)
        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return
        # TODO
        res = run_instance(example, client, image_name=self.image_name, logger=logger, work_dir=self.work_dir)
        if res is None:
            return
        # write
        with write_lock:
            with open(self.final_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(res) + '\n')
    
    def test_filter(self, max_workers=1):
        examples = load_jsonl(self.preprocess_fpath)
        out_path = self.final_fpath
        res = []
        if os.path.exists(out_path):
            res = load_jsonl(out_path)
        existing_ids = {i['instance_id'] for i in res}
        write_lock = Lock()
        if max_workers == 1:
            for i in tqdm(examples):
                self.process_example(i, existing_ids, write_lock)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_example, i, existing_ids, write_lock) for i in examples]
                for future in tqdm(
                    as_completed(futures),
                    total=len(examples),
                    colour="MAGENTA",
                ):
                    future.result()


def run_instance(
    example, 
    client,
    image_name='fb_xarray',
    logger=None, 
    work_dir='/root/xarray',
    proxy='http://127.0.0.1:7893'
):
    instance_id = example['instance_id']
    container = None
    patch_path = f'./patches/{instance_id}.patch'
    try:
        # build container
        container_name = f'{image_name}__{instance_id}'
        container = du.build_container(image_name=f'{image_name}:dev', container_name=container_name, client=client, logger=logger, proxy=proxy)
        container.start()
        # reset branch
        container.exec_run('git clean -fdx', workdir=work_dir)
        container.exec_run('git reset --hard HEAD', workdir=work_dir)
        # checkout base_commit 
        git_checkout_cmd = f"git checkout {example['execution']['base_commit']}"
        container.exec_run(git_checkout_cmd, workdir=work_dir)
        # apply test patch
        TEMP_PATCH = Path(patch_path)
        TEMP_PATCH.write_text(example['execution']['test_patch'])
        du.copy_to_container(container, TEMP_PATCH, PurePosixPath(DOCKER_PATCH))
        cmd_res = container.exec_run(f"git apply {DOCKER_PATCH}", workdir=work_dir)
        if cmd_res.exit_code != 0:
            logger.info(f"Failed to apply test patch to container")
            return None
        # get the config of the instance
        config = MAP_REPO_TO_CONFIG[example['repo']][example['execution']['version']]
        # run pre_install
        if 'pre_install' in config:
            for pre_install_cmd in config['pre_install']:
                cmd_res = container.exec_run(cmd=pre_install_cmd, workdir=work_dir)
        # conda activate and install
        cmd_res = container.exec_run(f"conda run -n {config['conda_env']} {config['install']}", workdir=work_dir)
        # before
        before_test_logs = []
        logger.info(f'begin to run tests(before)')
        for test_file in example['execution']['tests']:
            logger.info(f'begin to run test: {test_file}')
            test_cmd = f"conda run -n {config['conda_env'].strip()} {config['test_cmd'].strip()} {test_file}"
            # cmd_res = container.exec_run(test_cmd, workdir=work_dir)
            cmd_res = du.exec_run_with_timeout(container=container, cmd=test_cmd, workdir=work_dir, timeout=600)
            before_test_logs.append(cmd_res[0])
            logger.info(f"test log: {cmd_res}")
        
        # apply feature patch
        TEMP_PATCH.write_text(example['execution']['feature_patch'])
        du.copy_to_container(container, TEMP_PATCH, PurePosixPath(DOCKER_PATCH))
        cmd_res = container.exec_run(f"git apply {DOCKER_PATCH}", workdir=work_dir)
        if cmd_res.exit_code != 0:
            logger.info(f"Failed to apply feature patch to container")
            return None
        # conda activate and install
        config = MAP_REPO_TO_CONFIG[example['repo']][example['execution']['version']]
        cmd_res = container.exec_run(f"conda run -n {config['conda_env']} {config['install']}", workdir=work_dir)
        # after
        after_test_logs = []
        logger.info(f'begin to run tests(after)')
        for test_file in example['execution']['tests']:
            logger.info(f'begin to run test: {test_file}')
            test_cmd = f"conda run -n {config['conda_env'].strip()} {config['test_cmd'].strip()} {test_file}"
            cmd_res = du.exec_run_with_timeout(container=container, cmd=test_cmd, workdir=work_dir, timeout=600)
            after_test_logs.append(cmd_res[0])
            logger.info(f"test log: {cmd_res}")
        # analysis test log            
        PASS2PASS = []
        FAIL2PASS = []
        example['test'] = {
            'before': before_test_logs,
            'after': after_test_logs
        }

        before_content = '\n'.join(example['test']['before'])
        after_content = '\n'.join(example['test']['after'])
        
        # django dose not use pytest
        if 'django' in image_name:
            before_results = extract_django_tests(before_content)
            after_results = extract_django_tests(after_content)
        elif 'sympy' in image_name:
            before_results = extract_sympy_tests(before_content)
            after_results = extract_sympy_tests(after_content)
        elif any(i in image_name for i in ['pytest', 'sphinx']):
            before_results = extract_pytest_info(before_content, old=True)
            after_results = extract_pytest_info(after_content, old=True)
        elif any(i in image_name for i in ['requests']):
            before_results = extract_pytest_info_requests(before_content, old=True)
            after_results = extract_pytest_info_requests(after_content, old=True)
        else:
            before_results = extract_pytest_info(before_content)
            after_results = extract_pytest_info(after_content)
            
        after_passed = set([i[1] for i in after_results if i[0]=='PASSED'])
        before_dict = {i[1]: i[0] for i in before_results}
        for i in after_passed:
            if i in before_dict:
                before_test = before_dict[i]
                if before_test == 'PASSED':
                    PASS2PASS.append(i)
                else:
                    FAIL2PASS.append(i)
            else:
                FAIL2PASS.append(i)
        if len(FAIL2PASS) == 0:
            logger.info(f'Skip Collection: len(FAIL2PASS) == 0')
            return None
        example['tests'] = {
            "PASS2PASS": PASS2PASS,
            "FAIL2PASS": FAIL2PASS
        }
        return example
    except Exception as e:
        logger.error(f'error: {e}')
    finally:
        du.cleanup_container(client, container, logger)




if __name__ == '__main__':
    exe_filter = RequestsExeFilter()
    exe_filter.run()
