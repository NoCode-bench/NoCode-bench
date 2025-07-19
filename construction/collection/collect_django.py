import copy
import json
import requests
import os

from tqdm import tqdm
from utils.logger import get_logger
from utils.github import get_prs_by_commit
from utils.utils import run_cmd, dump_jsonl, load_jsonl

versions = [
    'remotes/origin/stable/5.1.x', 
    'remotes/origin/stable/4.2.x', 
    'remotes/origin/stable/3.2.x', 
    'remotes/origin/stable/2.2.x', 
    'remotes/origin/stable/1.9.x'
]
logger = get_logger('collect_django', 'logs/collect_django.log')

repo_owner = 'django'
repo_name = 'django'
repo_dir = 'repos/django/'
repo_url = 'https://github.com/django/django'

def process_release_notes():
    # 获取docs/ref下所有文件中的versionadded:: [x.x]的{文件路径, 代码行}
    # traverse dir to get all files
    directory = os.path.join(repo_dir, 'docs/ref')
    fpath_list = []
    for root, dirs, files in os.walk(directory):
        for name in files:
            fpath = os.path.join(root, name)
            normalized_fpath = fpath.replace('\\', '/')
            fpath_list.append(normalized_fpath)
    
    # get location in file
    keyword = 'versionadded::'
    update_lines = []
    for doc_fpath in fpath_list:
        try:
            doc_file = open(doc_fpath, 'r', encoding='utf-8')
            for line_number, line in enumerate(doc_file, start=1):
                if keyword in line:
                    normalized_doc_fpath = doc_fpath.replace(repo_dir, '')
                    item = {
                        'line_no': line_number,
                        'line': line,
                        'fpath': normalized_doc_fpath
                    }
                    update_lines.append(item)
        except UnicodeDecodeError as e:
            logger.error(f'{doc_fpath}:{e}')
            continue

    # get involved commithash by git blame
    commit_candidates = []
    for update in update_lines:
        git_cmd = f"git blame -L {update['line_no']},{update['line_no']} {update['fpath']}"
        logger.info(git_cmd)
        blame_res = run_cmd(git_cmd, repo_dir)
        # process blame_res
        if blame_res is None:
            continue
        blame_res = blame_res.strip()
        commit_hash = blame_res.split(' ')[0]
        commit_candidates.append(commit_hash)
    
    # get commit info by git show and api
    commit_show_candidates = []
    for commit_hash in commit_candidates:
        git_cmd = f'git show --format="commit: %H%nauthor: %an - %ae - %ad%ncommitter: %cn - %ce - %cd%nmessage: %s" {commit_hash}'
        logger.info(git_cmd)
        show_info = run_cmd(git_cmd, repo_dir)
        if show_info is None:
            continue
        show_info = show_info.strip()
        
        commit_show_candidates.append({
            'commit_hash': commit_hash,
            'commit_show': show_info
        })
    return commit_show_candidates

def get_all_commit_candidates():
    all_commits = []
    for version in versions:
        git_cmd = f'git checkout {version}'
        logger.info(git_cmd)
        cmd_res = run_cmd(git_cmd, repo_dir)
        if cmd_res is None:
            continue
        version_candidates = process_release_notes()
        for candidate in version_candidates:
            candidate['metadata'] = {
                'gh_url': repo_url,
                'branch': version,
            }
        all_commits.extend(version_candidates)

    return all_commits

def unify():
    examples = load_jsonl('cache/django_prs.jsonl')
    res = []
    # 去除没有pr的commit
    for example in examples:
        if len(example['prs']) != 1:
            continue
        
        pr_info = copy.deepcopy(example['prs'][0])
        pr_number = pr_info['html_url'].split('/')[-1]
        del pr_info['user']
        temp = {
            'repo': f'{repo_owner}/{repo_name}',
            'instance_id': f'{repo_owner}/{repo_name}-{pr_number}',
            'pr_info': pr_info,
            'metadata': example['metadata'],
        }
        res.append(temp)
    dump_jsonl(res, 'cache/unify/django.jsonl')
    # return res

if __name__ == '__main__':
    # commit_candidates = get_all_commit_candidates()
    # dump_jsonl(commit_candidates, 'cache/django.jsonl')
    # examples = load_jsonl('cache/django.jsonl')
    # remove duplicate examples
    # unique_examples = list({example['commit_hash']: example for example in examples}.values())
    
    # for example in tqdm(unique_examples):
    #     prs = get_prs_by_commit(repo_owner, repo_name, example['commit_hash'])
    #     if prs is None:
    #         logger.error(f'get_prs_by_commit error: {example["commit_hash"]}')
    #         continue
    #     example['prs'] = prs
    
    # dump_jsonl(unique_examples, 'cache/django_prs.jsonl')

    unify()
    print(1)