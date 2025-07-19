import time
import requests
import re
import os
from utils.utils import retry_request

token = ''
headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json'
}

base_url = 'https://api.github.com'

# os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
# os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

def get_prs_by_commit(owner, repo, commit_sha, retries=3):
    url = f'{base_url}/repos/{owner}/{repo}/commits/{commit_sha}/pulls'
    params = {'state': 'open'}  # 可选参数，如 'all', 'closed' 等
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code}")
                return []
        except Exception as e:
            if i < retries - 1:  # 如果不是最后一次尝试，则等待一段时间后重试
                sleep_time = 2 * (2 ** i)
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                return None

def extract_info_from_blame_line(line):
    # 定义正则表达式模式
    pattern = r"^(?P<commit_hash>[a-f0-9]{40}) $(?P<author>.+?) (?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}) (?P<line_number>\d+)$ (?P<content>.*)$"
    
    match = re.match(pattern, line)
    if match:
        return match.groupdict()
    else:
        print("No match found")
        return None



def get_related_prs_by_issue(owner, repo, issue_number, retries=3):
    url = f"{base_url}/repos/{owner}/{repo}/issues/{issue_number}/timeline"
    
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Error fetching timeline: {response.status_code}")
                return []
            else:
                events = response.json()
                related_prs = []
                
                for event in events:
                    if event['event'] == 'cross-referenced':
                        cross_issue = event.get('source').get('issue')
                        if cross_issue:
                            pr_info = cross_issue.get('pull_request', None)
                            if pr_info is None or pr_info['merged_at'] is None:
                                continue
                            # pr_match = re.search(r'/(\d+)$', pr_info['url'])
                            # if pr_match:
                            #     related_prs.append(pr_match.group(1))
                            related_prs.append(pr_info)
                return related_prs
        except Exception as e:
            if i < retries - 1:  # 如果不是最后一次尝试，则等待一段时间后重试
                sleep_time = 2 * (2 ** i)
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                return None


def get_milestone_ids(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/milestones?state=close&&direction=desc&&per_page=100"
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching milestones: {response.status_code}")
        return None
    
    milestones = response.json()
    feature_milestones = []
    pattern = r'^v\d+\.\d+\.0$'
    filter_keywords = ['fix', 'bug']
    for milestone in milestones:
        if not bool(re.fullmatch(pattern, milestone['title'])):
            continue
        lower_desc = milestone['description'].lower()
        if any(keyword in lower_desc for keyword in filter_keywords):
            continue
        feature_milestones.append(milestone)
        
    return feature_milestones

def list_issues_and_prs_by_q(owner, repo, q):
    query = f'repo:{owner}/{repo}+{q}'
    page = 1
    per_page = 100
    total_count = per_page
    items = []
    while True:
        url = f"{base_url}/search/issues?q={query}&&per_page={per_page}&&page={page}"
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching issues/PRs: {response.status_code}")
            return []
        res_json = response.json()
        total_count = res_json['total_count']
        # total_count = 100
        items.extend(res_json.get('items', []))
        if len(items) >= total_count:
            break
        else:
            page += 1
            if total_count - len(items) < 100:
                per_page = total_count - len(items)
    
    return items


def get_issue_info(owner, repo, issue_number, retries=3):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 检查请求是否成功
    
            data = response.json()
            return data
        except Exception as e:
            if i < retries - 1:  # 如果不是最后一次尝试，则等待一段时间后重试
                sleep_time = 2 * (2 ** i)
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                return None

def get_pr_info(repo, pr_id, retries=3):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_id}"
    res = retry_request(url, headers=headers, retries=retries)
    if res:
        return res.json()
    else:
        return None
    
