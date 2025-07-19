import copy
import os
import sys
sys.path.append(os.getcwd())
from tqdm import tqdm
from utils.utils import dump_jsonl, get_url_content, load_jsonl, PatchTools


cache_base_dir = './cache/unify/'

repo_info = {
    'astropy': {
        'ref_paths': ['docs/']
    },
    'django': {
        'ref_paths': ['docs/ref/', 'docs/'],
    },
    'flask': {
        'ref_paths': ['docs/']
    },
    'matplotlib': {
        'ref_paths': ['doc/en/reference', 'doc/']
    },
    'pylint': {
        'ref_paths': ['doc/']
    },
    'pytest': {
        'ref_paths': ['doc/en/', 'doc/']
    },
    'requests': {
        'ref_paths': ['docs/']
    },
    'scikit-learn': {
        'ref_paths': ['doc/']
    },
    'seaborn': {
        'ref_paths': ['doc/']
    },
    'sphinx': {
        'ref_paths': ['doc/']
    },
    'sympy': {
        'ref_paths': ['doc/']
    },
    'xarray': {
        'ref_paths': ['doc/']
    },
}


def get_diff_hunks(diff_content:str):
    diff_lines = diff_content.splitlines()
    diff_list = []
    # item: file diff_info
    temp_diff = []
    for line in diff_lines:
        strip_line = line.strip()
        if strip_line.startswith('diff --git a'):
            if temp_diff:
                diff_list.append(copy.deepcopy(temp_diff))
                temp_diff = []

        temp_diff.append(line)

    if temp_diff:
        diff_list.append(copy.deepcopy(temp_diff))
    try:
        res = []
        for diff in diff_list:
            old_path = ''
            new_path = ''
            for i in diff:
                if i.startswith('--- '):
                    old_path = i.replace('--- ', '')
                    if old_path.startswith('a/'):
                        old_path = old_path.replace('a/', '')
                elif i.startswith('+++ '):
                    new_path = i.replace('+++ ', '')
                    if new_path.startswith('b/'):
                        new_path = new_path.replace('b/', '')
                if old_path and new_path:
                    break
            res.append({
                'old_path': old_path,
                'new_path': new_path,
                'metadata': '\n'.join(diff)
            })
    except IndexError as e:
        return None
    return res

def check_diff(example, ref_paths=['docs/ref/'], modified_range=(1,1000)):
    # repo_owner = example['repo'].split('/')[0]
    # repo_name = example['repo'].split('/')[1]
    # pull_number = int(example['instance_id'].split('-')[-1])

    # get diff content and diff hunks
    # diff_url = f"https://github.com/{example['repo']}/pull/{pull_number}.diff"

    diff_content = example['diff_info']
    diffs = PatchTools.get_diff_hunks(diff_content)
    if not diffs:
        return False
    # meet the 3 limitations: 
        # non-test py code file
        # test file (has new test function)
        # ref doc file
    three_attr_flag = [0, 0, 0]
    # count the number of modified code files
    modified_counter = 0
    for diff_hunk in diffs:
        hunk_fpath = diff_hunk['new_path']
        # when deleting file, new_path will be a other string
        if hunk_fpath == '/dev/null':
            hunk_fpath = diff_hunk['old_path']
        if 'test' not in hunk_fpath and hunk_fpath.endswith('.py'):
            three_attr_flag[0] = 1
            modified_counter += 1
        if 'test' in hunk_fpath and three_attr_flag[1] == 0:
            three_attr_flag[1] = 1
            # get all new lines and judge if 'def' in line
            # temp_new_lines = [i for i in diff_hunk['metadata'].splitlines() if i.strip().startswith('def ')]
            # if not temp_new_lines:
            #     return False
        if any(i in hunk_fpath for i in ref_paths) and three_attr_flag[2] == 0:
            three_attr_flag[2] = 1
    if sum(three_attr_flag) != 3:
        return False
    
    if modified_counter not in range(*modified_range):
        return False
    return True

def get_examples_diff_info(examples, fout):

    print(f'starting to read {fout}')

    def get_diff_info(example):
        pull_number = int(example['instance_id'].split('-')[-1])
        diff_url = f"https://patch-diff.githubusercontent.com/raw/{example['repo']}/pull/{pull_number}.diff"
        diff_content = get_url_content(diff_url)
        return diff_content

    if os.path.exists(fout):
        return load_jsonl(fout)
    res = []
    for example in tqdm(examples):
        diff_content = get_diff_info(example)
        if diff_content:
            example['diff_info'] = diff_content
            res.append(example)
    
    dump_jsonl(res, fout)
    return res

if __name__ == "__main__":
    for repo in repo_info:
        examples = load_jsonl(f'{os.path.join(cache_base_dir, repo)}.jsonl')
        examples_with_diff_out = f'{os.path.join(cache_base_dir, "cache/", repo)}_with_diff.jsonl'
        examples_with_diff = get_examples_diff_info(examples, fout=examples_with_diff_out)

        examples_diffchecked = []
        print(repo)
        for example in examples_with_diff:
            if check_diff(example, repo_info[repo]['ref_paths'], (0,99)):
                examples_diffchecked.append(example)
        examples_with_diff_filter_out = f'{os.path.join("cache/attribute", repo)}_with_diff_filter.jsonl'
        dump_jsonl(examples_diffchecked, examples_with_diff_filter_out)
        print(len(examples_diffchecked))