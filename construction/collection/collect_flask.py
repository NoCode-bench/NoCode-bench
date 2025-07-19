from lxml import html
from tqdm import tqdm
from utils.github import get_related_prs_by_issue
import copy

from utils.logger import get_logger
from utils.utils import dump_jsonl, load_jsonl

owner = "pallets"
repo = "flask"
logger = get_logger('collect_flask', 'logs/collect_flask.log')

def changes_filter_by_heuristic(comment: str):
    lower_comment = comment.lower()
    return lower_comment.startswith('fix') or ('update' in lower_comment) or ('deprecated code' in lower_comment) or ('drop support' in lower_comment) or ('dependency' in lower_comment and ('>' in lower_comment or '<' in lower_comment))

def normalize_href(hrefs: list[str]):
    norm_hrefs = []
    has_pr = False
    pull_url = 'https://github.com/pallets/flask/pull/'
    issues_url = 'https://github.com/pallets/flask/issues/'
    for href in hrefs:
        href_type = -1
        temp_id = ''
        if pull_url in href:
            href_type = 'pr'
            has_pr = True
            temp_id = href.replace(pull_url, '').strip()
        elif issues_url in href:
            href_type = 'issue'
            temp_id = href.replace(issues_url, '').strip()
        else:
            continue
        norm_hrefs.append({
            'type': href_type,
            'id': temp_id
        })
    if has_pr:
        norm_hrefs = [i for i in norm_hrefs if i['type'] == 'pr']
    res = []
    for href in norm_hrefs:
        if ',%20' in href['id']:
            temp = href['id'].split(',%20')
            for i in temp:
                res.append({'type': href['type'], 'id': i})
        else:
            res.append(href)
    return res

def process_release_notes():
    changes_content = open('repos/flask_changes.html', 'r', encoding='utf-8').read()

    tree = html.fromstring(changes_content)

    sections = tree.xpath('/html/body/div[2]/div[1]/div/div/section/section')
    all_updates = []
    for section in sections:
        version_updates = []
        version = section.xpath('h2')[0].text
        release_info = section.xpath('p/text()')[0]
        update_list = section.xpath('ul/li')
        for update in update_list:
            # try:
            update_comment = update.xpath('p')[0].text_content()
            update_a_texts = update.xpath('p/a/text()')
            if len(update_a_texts) == 0:
                continue
            update_a_hrefs = update.xpath('p/a/@href')
            # only store the href of issue and pr
            update_ids = normalize_href(update_a_hrefs)
            if update_ids is None:
                continue
            final_comment = update_comment.replace(''.join(update_a_texts), '').strip()
            if changes_filter_by_heuristic(final_comment):
                continue
            if update_ids:
                version_updates.append({
                    'desc': final_comment,
                    'links': update_ids
                })
            # except IndexError as e:
            #     continue
        
        if version_updates:
            for update in version_updates:
                update['version'] = version
                update['release_info'] = release_info
            all_updates.extend(version_updates)


    return all_updates


def unify():
    examples = load_jsonl(f'cache/{repo}_prs.jsonl')
    res = []
    # 去除没有pr的commit
    for example in examples:
        if not isinstance(example['prs'], list):
            example['prs'] = [example['prs']]
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
    # all_updates = process_release_notes()
    # res_updates = []
    # for update in tqdm(all_updates):
    #     for link in update['links']:
    #         if link['type'] == 'issue':
    #             pr_id = -1
    #             related_prs = get_related_prs_by_issue(owner, repo, link['id'])
    #             if not related_prs:
    #                 continue
    #             res_updates.append({
    #                 'prs': related_prs,
    #                 'metadata': update
    #             })
    #         elif link['type'] == 'pr':
    #             related_prs = {
    #                 "url": f"https://api.github.com/repos/pallets/flask/pulls/{link['id']}", 
    #                 "html_url": f"https://github.com/pallets/flask/pull/{link['id']}", 
    #                 "diff_url": f"https://github.com/pallets/flask/pull/{link['id']}.diff", 
    #                 "patch_url": f"https://github.com/pallets/flask/pull/{link['id']}.patch", 
    #                 "merged_at": "unknown"
    #             }
    #             res_updates.append({
    #                 'prs': related_prs,
    #                 'metadata': update
    #             })
    # dump_jsonl(res_updates, 'cache/flask_prs.jsonl')
    unify()