import re


def extract_pytest_info(test_content: str, old=False):
    test_content = re.sub(
        r'ERROR conda\.cli\.main_run:execute\(\d+\): .*? failed\. \(See above for error\)\n',
        '',
        test_content
    )
    test_content = re.sub(
        r'<frozen importlib._bootstrap>:241: RuntimeWarning: numpy.ndarray size changed, may indicate binary incompatibility. Expected 88 from C header, got 96 from PyObject\n\n',
        '',
        test_content
    )

    lines = test_content.splitlines()
    res = []
    option_pattern = re.compile(r"(.*?)\[(.*)\]")

    for line in lines:
        parts = line.split(' ', 1)
        if parts[0] not in ['PASSED', 'FAILED', 'ERROR', 'XFAIL']:
            continue
        if parts[0] == 'ERROR' and 'conda.cli.main_run' in parts[1]:
            continue
        has_option = option_pattern.search(parts[1])
        if has_option:
            main, option = has_option.groups()
            test_name = f"{main}[{option}]"
        else:
            test_name = parts[1]
        res.append((parts[0], test_name))

    if old:
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ['PASSED', 'ERROR', 'FAILED', 'XFAIL']:
                res.append((parts[1], parts[0]))

    return res


# -------------- old -----------------

def extract_pytest_info_v1(test_content: str, old=False):
    lines = test_content.splitlines()
    res = []
    option_pattern = re.compile(r"(.*?)\[(.*)\]")
    for line in lines:
        parts = line.split(' ', 1)
        if parts[0] not in ['PASSED', 'FAILED', 'ERROR', 'XFAIL']:
            continue
        if parts[0] == 'ERROR' and 'conda.cli.main_run' in parts[1]:
            continue
        has_option = option_pattern.search(parts[1])
        if has_option:
            main, option = has_option.groups()
            test_name = f"{main}[{option}]"
        else:
            test_name = parts[1]

        if 'ERROR conda.cli.main_run' in test_name:
            test_name = test_name.split('ERROR conda.cli.main_run')[0]

        res.append((parts[0], test_name))

    if old:
        # 旧版本格式是 "<file> <STATUS>"，比如 "test_file.py PASSED"
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ['PASSED', 'ERROR', 'FAILED', 'XFAIL']:
                res.append((parts[1], parts[0]))

    return res


def extract_pytest_info_old1(test_content, old=False):
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
