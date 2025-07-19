import glob
import os
from pathlib import Path
import re
import subprocess
import json
import time
import requests
from lxml import html
from unidiff import PatchSet

# os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
# os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

def run_cmd(command, cwd=None, print_err=True, logger=None, timeout=None):
    try:
        # 运行命令并捕获输出
        result = subprocess.run(
            command,
            shell=True,  # 在 Windows 上建议设置为 True
            check=True,  # 如果命令失败则抛出 CalledProcessError 异常
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # 返回字符串而不是字节对象
            encoding='utf-8',
            timeout=timeout,
            cwd=cwd  # 设置工作目录
        )
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        if logger:
            logger.info(f"An error occurred while running the command: {e.stderr}")
        # if print_err:
        #     print(f"An error occurred while running the command: {e.stderr}")
        return None
    except OSError as e:
        return None
    
def run_cmd_with_err(command, cwd=None, timeout=None):
    try:
        # 运行命令并捕获输出
        result = subprocess.run(
            command,
            shell=True,  # 在 Windows 上建议设置为 True
            check=True,  # 如果命令失败则抛出 CalledProcessError 异常
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # 返回字符串而不是字节对象
            encoding='utf-8',
            timeout=timeout,
            cwd=cwd  # 设置工作目录
        )
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr
    except subprocess.TimeoutExpired as e:
        return None

def dump_jsonl(examples, fpath):
    with open(fpath, 'w', encoding='utf-8') as f:
        for line in examples:
            f.write(json.dumps(line) + '\n')

def load_jsonl(fpath):
    with open(fpath, 'r', encoding='utf-8') as f:
        lines = []
        for line in f:
            lines.append(json.loads(line))
        return lines
    

def get_url_content(url):
    # try:
    response = retry_request(url)

    if response:
        return response.text
    else:
        return None


def retry_request(url, retries=3, headers=None):
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 检查请求是否成功
            return response
        except Exception as e:
            if i < retries - 1:  # 如果不是最后一次尝试，则等待一段时间后重试
                sleep_time = 2 * (2 ** i)
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                return None
            
            
def list_all_files(directory):
    
    file_list = []
    files_recursive = glob.glob(f"{directory}/**/*", recursive=True)

    for file in files_recursive:
        if Path(file).is_file():
            file_list.append(file)
    return file_list


def extract_diff_content(diff):
    pattern = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@.*\n((?:(?!^@@).*\n?)*)", re.MULTILINE)
    matches = pattern.findall(diff)
    return ''.join(matches).rstrip('\n')


def get_django_issue_report(issue_id):
    url = f'https://code.djangoproject.com/ticket/{issue_id}'
    issue_page = get_url_content(url)
    tree = html.fromstring(issue_page)

    searchable = tree.xpath('//div[@class="searchable"]')[0]
    issue_content = searchable.text_content().strip()
    return issue_content


class PatchTools:
    
    @staticmethod
    def get_diff_hunks(patch):
        patch_set = PatchSet(patch)
        return [
            {
                'path': i.path,
                'old_path': i.source_file,
                'new_path': i.target_file,
                'metadata': str(i)
            } for i in patch_set
        ]
        
    @staticmethod
    def get_patches(patch, test_words=None):
        feature_patch = ""
        test_patch = ""
        test_words = ["test", "tests", "e2e", "testing"] if test_words is None else test_words
        for hunk in PatchSet(patch):
            if any(
                test_word in hunk.path for test_word in test_words
            ):
                test_patch += str(hunk)
            else:
                feature_patch += str(hunk)
        return feature_patch, test_patch
    
    
from tqdm import tqdm
class IssueReportGetter:
    def __init__(self, eval_file):
        fpath1 = 'cache/unify/django.jsonl'
        fpath2 = eval_file
        all_exmaples = load_jsonl(fpath1)

        examples = load_jsonl(fpath2)

        ids = [i['instance_id'] for i in examples]
        self.id2report = {}
        temps = [i for i in all_exmaples if i['instance_id'] in ids]
        for example in tqdm(temps):
            ins_id = example['instance_id']
            if ins_id in ids:
                title = example['pr_info']['title']
                pattern = r'#(\d+)'
                match = re.search(pattern, title)
                issue_report = ''
                if match:
                    issue_id = match.group(1)
                    issue_report = get_django_issue_report(issue_id)
                self.id2report[ins_id] = issue_report
                
    def store(self, path='cache/django_issue_report.json'):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.id2report))
                
if __name__ == '__main__':
    isg = IssueReportGetter('datasets/lite_django_1mod.jsonl')
    isg.store()