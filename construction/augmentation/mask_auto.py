import re

def mask_information(doc, i=-1):
    pr_pattern_1 = re.compile(r"(?:issue|pull|pr):`(\d+)`")
    pr_pattern_2 = re.compile(r"(\d+)\.(?:trivial|bugfix|feature|other|api|breaking|new_check)")
    pr_pattern_3 = re.compile(r"(?:\*|Closes) #(\d+)")
    pr_pattern_4 = re.compile(r"GH(\d+)")
    pr_pattern_5 = re.compile(r"\[(?:#\d+(?:,\s*)?)+\]")
    pr_pattern_6 = re.compile(r"\(refs: #(\d+)\)")
    pr_pattern_7 = re.compile(r"<https://github.com/[\w/]*/issues/(\d+)>")
    pr_pattern_8 = re.compile(r"(\d+)-(?:GL|AL)")
    
    name_pattern_1 = re.compile(r"user:`([^`]+)`")
    name_pattern_2 = re.compile(r"(?:by |By )`([^`]+)`_")
    name_pattern_3 = re.compile(r"by `([^`]+<[^`]>)`")
    name_pattern_4 = re.compile(r"By ([^`]*?`<https://github.com/[^>]*?>`)")
    name_pattern_5 = re.compile(r"`[^`]*?<https://github.com/[^>/]*?>`")
    
    pr_patterns = [pr_pattern_1, pr_pattern_2, pr_pattern_3, pr_pattern_4, pr_pattern_6, pr_pattern_7, pr_pattern_8]
    for pattern in pr_patterns:
        match = re.findall(pattern, doc)
        if match:
            print(f"{i} - {pattern}: {match}")
            for string in match:
                doc = doc.replace(string, "<PRID>")
    
    match = re.findall(pr_pattern_5, doc)
    if match:
        print(f"{i} - {pr_pattern_5}: {match}")
        for string in match:
            pr_numbers = re.findall(r'#(\d+)', string)
            for pr_number in pr_numbers:
                doc = doc.replace(pr_number, "<PRID>")
        
    
    name_patterns = [name_pattern_1, name_pattern_2, name_pattern_3, name_pattern_4, name_pattern_5]
    for pattern in name_patterns:
        match = re.findall(pattern, doc)
        if match:
            print(f"{i} - {pattern}: {match}")
            for string in match:
                doc = doc.replace(string, "<NAME>")
                
    return doc


if __name__ == '__main__':
    # read the file and call the mask_information for every instance
    pass