from tqdm import tqdm
from utils.github import get_milestone_ids, get_related_prs_by_issue, list_issues_and_prs_by_q
from utils.logger import get_logger
from utils.utils import dump_jsonl, load_jsonl

owner = "sympy"
repo = "sympy"
logger = get_logger('collect_sympy', 'logs/collect_sympy.log')

def process_release_notes():
        q = f'label:Enhancement+is:closed+reason:completed'
        res_prs = []
        # search prs
        issues_and_prs = list_issues_and_prs_by_q(owner, repo, q)
        # get pr for issue
        for item in tqdm(issues_and_prs):
            if 'pull_request' in item:
                 item['prs'] = [item['pull_request']]
                 res_prs.append(item)
                 continue
            issue_number = item['number']
            related_prs = get_related_prs_by_issue(owner, repo, issue_number)
            if not related_prs:
                 continue
            item['prs'] = related_prs

        return res_prs


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
               #  'metadata': example['metadata'],
            }
            res.append(temp)
    dump_jsonl(res, f'cache/unify/{repo}.jsonl')

if __name__ == '__main__':
#     prs = process_release_notes()
#     dump_jsonl(prs, 'cache/sympy_prs.jsonl')

     unify()