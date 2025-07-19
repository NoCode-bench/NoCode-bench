import json
import os
from tree_sitter_languages import get_language, get_parser
from tqdm import tqdm

from utils.utils import PatchTools, load_jsonl, dump_jsonl, run_cmd
from unidiff import PatchSet

language = get_language('python')
parser = get_parser('python')

SEPARATOR = '\u2E80'  # 一个 CJK 拼音扩展区的字符，极少出现在普通文本中

PATCH_FILE = './test.patch'

def _get_raise_string(node):
    if node.type not in ['raise_statement', 'with_clause']:
        return
    # if node.type == 'with_statement' and 'pytest.raises' not in node.text.decode():
    string_node = None
    node_arrs = ['raise_statement', 'call', 'argument_list', 'string', 'string_content']
    def traverse(node, pos):
        if (pos <= 2 and node.type != node_arrs[pos]):
            return
        if node.type == node_arrs[-1]:
            nonlocal string_node
            string_node = node
            return
        for child in node.named_children:
            pos += 1
            traverse(child, pos)
            pos -= 1
    
    if node.type == 'raise_statement':
        traverse(node, 0)
    elif 'pytest.raises' in node.text.decode():
        call_nodes = []
        def get_call_nodes(root):
            for child in root.named_children:
                if child.type == 'call':
                    call_nodes.append(child)
                else:
                    get_call_nodes(child)
        get_call_nodes(node)
        if call_nodes:
            traverse(call_nodes[0], 1)
        
    if string_node is not None:
        return string_node.text.decode()
    
    return None

def get_all_identifers(root):
    res = []
    
    def traverse(node):
        if node.type == 'identifier':
            id_type = 'field'
            if node.parent.type in ['function_definition', 'class_definition']:
                id_type = {
                    'function_definition': 'function',
                    'class_definition': 'class',
                }[node.parent.type]
            res.append({
                'name': node.text.decode(),
                'type': id_type,
            })
        
        # 处理raise语句
        if node.type in ['raise_statement', 'with_clause']:
            raise_str = _get_raise_string(node)
            if raise_str is not None:
                res.append({
                    'name': raise_str,
                    'type': 'error_msg',
                })
            
        for child in node.named_children:
            traverse(child)
    
    traverse(root)
    return res

def get_diff_entities(example, repo_dir, patch_type='feature'):
    
    def read_code(file_path):
        if not os.path.exists(file_path):
            return ''
        with open(file_path, 'r') as f:
            return f.read()
    
    base_commit = example['base_commit']
    # -------------切换到对应的commit
    run_cmd('git clean -fdx', repo_dir)
    run_cmd('git reset --hard HEAD', repo_dir)
    git_checkout_cmd = f'git checkout {base_commit}'
    git_checkout_res = run_cmd(git_checkout_cmd, repo_dir)
    # -------------获取diff文件
    patch_content = example['feature_patch'] if patch_type == 'feature' else example['test_patch']
    patch_set = PatchSet(patch_content)
    patched_files = [i for i in patch_set if i.path.endswith('.py')]
    # 获取所有patched_files的ids
    diff_ids = {}
    for patched_file in patched_files:
        fpath = patched_file.path
        before_code = read_code(os.path.join(repo_dir, fpath))
        root = parser.parse(before_code.encode()).root_node
        before_ids = get_all_identifers(root)
        diff_ids[fpath] = {}
        diff_ids[fpath]['before'] = before_ids
    # -------------应用patch
    with open(PATCH_FILE, 'w') as f:
        f.write(patch_content)
    patch_res = run_cmd(f'git apply {PATCH_FILE}', repo_dir)
    for patched_file in patched_files:
        fpath = patched_file.path
        before_code = read_code(os.path.join(repo_dir, fpath))
        root = parser.parse(before_code.encode()).root_node
        after_ids = get_all_identifers(root)
        diff_ids[fpath]['after'] = after_ids
    
    # -------------获取新增的entity
    entity_ids = set()
    for i in diff_ids:
        old_ids = diff_ids[i]['before']
        new_ids = diff_ids[i]['after']
        for new_id in new_ids:
            flag = True
            for old_id in old_ids:
                if new_id['type'] == old_id['type'] and new_id['name'] == old_id['name']:
                    flag = False
                    break
            if flag:
                entity_ids.add(SEPARATOR.join([i, new_id['type'], new_id['name']]))
    return entity_ids

def get_new_entities(example, repos_dir):
    repo_name = example['repo'].split('/')[-1]
    base_commit = example['base_commit']
    
    feature_patch = example['feature_patch']
    test_patch = example['test_patch']
    repo_dir = os.path.join(repos_dir, repo_name)

    # 获取feature_patch相关文件前后新增的实体（包含新增文件）
    feature_patch_set = PatchSet(feature_patch)
    new_files_entities = [{
        'name': i.path,
        'type': 'file',
    } for i in feature_patch_set.added_files if i.path.endswith('.py')]
    feature_entities = get_diff_entities(example, repo_dir, 'feature')
    # 获取test_patch相关文件前后新增的实体
    test_entities = get_diff_entities(example, repo_dir, 'test')
    # 寻找在test_patch中新增的实体，同时也在feature_patch中新增的实体
    test_entities_names = set([i.split(SEPARATOR)[-1] for i in test_entities])
    new_ids_filter_by_test = []
    for i in feature_entities:
        if i.split(SEPARATOR)[-1] in test_entities_names:
            new_ids_filter_by_test.append(i)
    # 检查新增的实体是否出现在文档中，获得为出现的实体
    new_ids_filter_by_test += [SEPARATOR.join([i['name'], i['type'], i['name']]) for i in new_files_entities]
    doc_content = '\n'.join([i['metadata'] for i in example['doc_changes']])
    new_entities = set()
    for i in new_ids_filter_by_test:
        if i.split(SEPARATOR)[-1] not in doc_content:
            new_entities.add(i)
    return new_entities


def main(in_fpath, out_fpath):
    repos_dir = 'repos'
    # in_fpath = 'results/verification/fb-verified_v0.1_masked.jsonl'
    examples = load_jsonl(in_fpath)
    for example in tqdm(examples):
        entities = get_new_entities(example, repos_dir)
        res = []
        for i in entities:
            parts = i.split(SEPARATOR)
            res.append({
                'type': parts[1],
                'name': parts[2],
            })
        example['augmentations'] = {
            'header': 'If completing this task requires creating new files, classes, fields, or error messages, you may consider using the following suggested entity names:',
            'data': res
        }
    
    dump_jsonl(examples, out_fpath)
    
if __name__ == '__main__':
    main('results/execution/fb-full_v0.1_fulldoc.jsonl', 'results/augmentation/fb-full_v0.1_augmented.jsonl')
