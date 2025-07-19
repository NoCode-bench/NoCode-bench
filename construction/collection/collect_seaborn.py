from tqdm import tqdm
from utils.github import get_milestone_ids, get_related_prs_by_issue, list_issues_and_prs_by_q
from utils.logger import get_logger
from utils.utils import dump_jsonl, load_jsonl

owner = "mwaskom"
repo = "seaborn"
logger = get_logger('collect_seaborn', 'logs/collect_seaborn.log')

def process_release_notes():
        q1 = f'label:"feature"+is:closed+reason:completed'
        q2 = f'label:"enhancement"+is:closed+reason:completed'
        res_prs = []
        # search prs
        issues_and_prs1 = list_issues_and_prs_by_q(owner, repo, q1)
        issues_and_prs2 = list_issues_and_prs_by_q(owner, repo, q2)
        issues_and_prs = issues_and_prs1 + issues_and_prs2
        # remove duplication
        seen_ids = set()
        unique_prs = []
        for i in issues_and_prs:
             if i['id'] not in seen_ids:
                  unique_prs.append(i)
                  seen_ids.add(i['id'])
        # get pr for issue
        for item in tqdm(unique_prs):
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

# out of date: backup
# def process_release_notes():
#     # get related milestone
#     milestones = get_milestone_ids(owner, repo)

#     normalized_prs = []
#     prid_set = set()
#     filter_keywords = ['bug', 'fix', 'backport pr']
#     for milestone in tqdm(milestones):
#         milestone_title = milestone['title']
#         q = f'milestone:{milestone_title}+is:closed'
#         # search prs
#         prs = list_issues_and_prs_by_q(owner, repo, q)
#         # filter out duplicated items and non-feature items
#         for pr in prs:
#             lower_title = pr['title'].lower()
#             if any(keyword in lower_title for keyword in filter_keywords):
#                 continue
#             if pr['number'] in prid_set:
#                 continue
#             prid_set.add(pr['number'])
#             normalized_prs.append(pr)
#     return normalized_prs

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
#     dump_jsonl(prs, 'cache/seaborn_prs.jsonl')
     unify()