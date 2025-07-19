from lxml import etree
import re

from tqdm import tqdm

from utils.github import get_issue_info, get_related_prs_by_issue
from utils.utils import dump_jsonl, load_jsonl

owner = "astropy"
repo = "astropy"


def process_release_notes():
    change_logs = open('repos/astropy_changes.html', 'r', encoding='utf-8').read()

    tree = etree.HTML(change_logs)
    update_items = []
    # version
    version_sections = tree.xpath('//section/section[contains(@id, "version")]')
    for version_section in version_sections:
        version_title = version_section.xpath('./h2/text()')[0].strip()
        big_functions = version_section.xpath("./section/h3[contains(text(), 'New Features')]/following-sibling::section")
        # big function: has many small update item
        for big_function in big_functions:
            big_function_title = big_function.xpath('./h4/text()')[0].strip().lower()
            # item: get update items and filter some items by conditions
            items = big_function.xpath('ul/li')
            for item in items:
                desc = item.xpath('string(.)').strip()
                # extract issue_number
                match = re.search(r'\[#\d{1,5}\]$', desc)
                if not match:
                    continue
                
                update_items.append({
                    'issue_number': match.group()[2:-1],
                    'desc': f'{big_function_title}: {desc}',
                    'version': version_title,
                })
    return update_items

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
    
    # dump_jsonl(res, 'cache/astropy_prs.jsonl')
    unify()