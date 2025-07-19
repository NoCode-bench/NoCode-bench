import re
from lxml import etree
from utils.utils import get_url_content, dump_jsonl, load_jsonl
import os
from tqdm import tqdm

from utils.github import get_issue_info, get_related_prs_by_issue
from utils.utils import dump_jsonl

owner = "scikit-learn"
repo = "scikit-learn"

def get_release_notes():
    out_fpath = 'repos/scikitlearn_change.jsonl'
    version_list = ['1.6', '1.5', '1.4', '1.3', '1.2', '1.1', '1.0', '0.24', '0.23', '0.22', '0.21', '0.20', '0.19', '0.18', '0.17', '0.16', '0.15', '0.14', '0.13']
    if os.path.exists(out_fpath) and os.path.isfile(out_fpath):
        return load_jsonl(out_fpath)
    release_notes_pages = []
    for version in version_list:
        release_notes_url = f'https://scikit-learn.org/stable/whats_new/v{version}.html'
        url_content = get_url_content(release_notes_url)
        release_notes_pages.append({
            'version': version,
            'html': url_content
        })
    dump_jsonl(release_notes_pages, out_fpath)
    return release_notes_pages

def process_release_notes():
    release_notes = get_release_notes()
    updates = []
    for release_note in release_notes:
        tree = etree.HTML(release_note['html'])
        update_li_list = tree.xpath("//span[(@class='badge text-bg-success' and contains(text(), 'Feature')) or (@class='badge text-bg-info' and contains(text(), 'Enhancement'))]/ancestor::li")
        for update in update_li_list:
            desc = update.xpath('string(.)').strip()
            match = re.search(r'#\d{1,5}', desc)
            if not match:
                continue
            
            updates.append({
                'issue_number': match.group()[1:],
                'desc': desc,
                'version': release_note['version'],
            })
    return updates

def unify():
    examples = load_jsonl(f'cache/{repo}_prs.jsonl')
    res = []
    # 去除没有pr的commit
    for example in examples:
        temp_prs = [i for i in example['prs'] if f'{owner}/{repo}/' in i['html_url']]
        if len(temp_prs) == 0:
            continue
        for temp_pr in temp_prs:
            pr_info = temp_pr
            pr_number = pr_info['html_url'].split('/')[-1]
            temp = {
                'repo': f'{owner}/{repo}',
                'instance_id': f'{owner}/{repo}-{pr_number}',
                'pr_info': pr_info,
                'metadata': example['metadata'],
            }
            res.append(temp)
    dump_jsonl(res, f'cache/unify/{repo}.jsonl')

if __name__ == '__main__':
    # updates = process_release_notes()
    # res = []
    # for update in tqdm(updates):
    #     issue_number = update['issue_number']
    #     issue_info = get_issue_info(owner, repo, issue_number)
    #     prs = []
    #     issue_type = ''
    #     if 'pull_request' in issue_info:
    #         prs = [issue_info['pull_request']]
    #         issue_type = 'pr'
    #     else:
    #         prs = get_related_prs_by_issue(owner, repo, issue_number)
    #         issue_type = 'issue'
    #     if prs:
    #         res.append({
    #             'prs': prs,
    #             'metadata': {
    #                 'original_type': issue_type,
    #                 'update_info': update
    #             }
    #         })
    
    # dump_jsonl(res, 'cache/scikit-learn_prs.jsonl')

    unify()