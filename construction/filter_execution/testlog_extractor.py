import re

def extract_pytest_info(test_content, old=False):
    lines = test_content.splitlines()
    # if not old:
    res = [tuple(line.split()[:2]) for line in lines if any([line.startswith(i) for i in ['ERROR ', 'FAILED ', 'PASSED ', 'XFAIL ']])]
    if old:
        # res = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ['PASSED', 'ERROR', 'FAILED', 'XFAIL']:
                res.append(tuple([parts[1], parts[0]]))
    return res


def extract_sympy_tests(tests_content):
    lines = tests_content.splitlines()
    lines = [line.strip() for line in lines]
    res = []
    test_map = {'ok': 'PASSED', 'F': 'FAILED', 'E': 'ERROR', 'f': 'XFAIL'}
    for line in lines:
        line = line.strip()
        if line.startswith('test_') and any([line.endswith(i) for i in [' E', ' ok', ' F', ' f']]):
            parts = line.split()
            res.append((test_map[parts[-1]], parts[0]))
    return res

def extract_django_tests(tests_content):
    test_lines = tests_content.splitlines()
    tests = []
    pattern = r'test_.+? \(.+?\)'
    test_lines.reverse()
    test_map = {'ok': 'PASSED', 'FAIL': 'FAILED', 'ERROR': 'ERROR'}
    for i in range(len(test_lines)):
        line = test_lines[i]
        if line.startswith('test_') and any(line.endswith(i) for i in ['... ok', '... ERROR', '... FAIL']):
            matches = re.findall(pattern, line)
            test_name = matches[-1].strip()
            test_res = line.split(' ... ')[-1].strip()
            tests.insert(0, (test_map[test_res], test_name))
        elif any(line.endswith(i) for i in ['... ok', '... ERROR', '... FAIL']) and not line.startswith('test_'):
            test_name = ''
            test_res = line.split(' ... ')[-1].strip()
            # look up util finding test name
            while i < len(test_lines) - 1:
                i += 1
                line = test_lines[i]
                match = re.findall(pattern, line)
                if match:
                    test_name = match[-1]
                    tests.insert(0, (test_map[test_res], test_name))
                    break 
    return tests
