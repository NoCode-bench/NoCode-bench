import re
import os

from tqdm import tqdm
from utils.github import get_issue_info, get_related_prs_by_issue
from utils.utils import dump_jsonl, load_jsonl


repo_owner = 'pylint-dev'
repo_name = 'pylint'

repo_dir = 'repos/pylint/'

def extract_update_item(updates_str:str, sep=('*','-')):
    str_lines = updates_str.strip().splitlines()
    res = []
    temp_update = []
    for line in str_lines:
        if line.startswith(sep):
            if temp_update:
                res.append(temp_update)
                temp_update = []
            temp_update.append(line)
        else:
            if line.strip():
                temp_update.append(line)
    
    if temp_update:
        res.append(temp_update)
    
    issue_pattern = r'(?:Closes|Refs)\s{0,1}#\s{0,1}(\d*)'

    update_res = []
    for lines in res:
        issue_ids = re.findall(issue_pattern, lines[-1])
        if issue_ids:
            update_res.append({
                'desc': '\n'.join(lines[:-1]),
                'issue_number': issue_ids[0]
            })

    return update_res


def process_release_notes():
    directory = os.path.join(repo_dir, 'doc/whatsnew')
    fpath_list = []

    pattern1 = r'Extensions\s*=+\s*(.*?)Other\sChanges'
    pattern2 = r'New Features\s*-+\s*(.*?)(?:False\sPositives\sFixed|New\sChecks)'
    pattern3 = r'New Checks\s*-+\s*(.*?)\n\n\n'

    # get all doc files
    for root, dirs, files in os.walk(directory):
        for name in files:
            fpath = os.path.join(root, name)
            normalized_fpath = fpath.replace('\\', '/')
            fpath_list.append(normalized_fpath)

    # get update item
    update_list = []
    for doc_fpath in fpath_list:
        try:
            doc_file = open(doc_fpath, 'r', encoding='utf-8')
            doc_content = doc_file.read().strip()
            match1 = re.findall(pattern1, doc_content, re.DOTALL)
            match2 = re.findall(pattern2, doc_content, re.DOTALL)
            match3 = re.findall(pattern3, doc_content, re.DOTALL)
            match = list(set(match1 + match2 + match3))
            if match:
                for i in match:
                    # print(i.strip())
                    for update in extract_update_item(i):
                        update['release_note'] = doc_fpath.replace(repo_dir, '')
                        update_list.append(update)
        except UnicodeDecodeError as e:
            continue
    
    return update_list


def unify():
    examples = load_jsonl(f'cache/{repo_name}_prs.jsonl')
    res = []
    # 去除没有pr的commit
    for example in examples:
        temp_prs = [i for i in example['prs'] if f'{repo_owner}/{repo_name}/' in i['html_url']]
        if len(temp_prs) == 0:
            continue
        for temp_pr in temp_prs:
            pr_info = temp_pr
            pr_number = pr_info['html_url'].split('/')[-1]
            temp = {
                'repo': f'{repo_owner}/{repo_name}',
                'instance_id': f'{repo_owner}/{repo_name}-{pr_number}',
                'pr_info': pr_info,
                'metadata': example['metadata'],
            }
            res.append(temp)
    dump_jsonl(res, f'cache/unify/{repo_name}.jsonl')

if __name__ == '__main__':
    # updates = process_release_notes()
    # res = []
    # for update in tqdm(updates):
    #     issue_number = update['issue_number']
    #     issue_info = get_issue_info(repo_owner, repo_name, issue_number)
    #     prs = []
    #     issue_type = ''
    #     if 'pull_request' in issue_info:
    #         prs = [issue_info['pull_request']]
    #         issue_type = 'pr'
    #     else:
    #         # 后一个pr大概率是大版本的pr
    #         prs = get_related_prs_by_issue(repo_owner, repo_name, issue_number)
    #         issue_type = 'issue'
    #     if prs:
    #         res.append({
    #             'prs': prs,
    #             'metadata': {
    #                 'original_type': issue_type,
    #                 'update_info': update
    #             }
    #         })
    
    # dump_jsonl(res, 'cache/pylint_prs.jsonl')
    unify()