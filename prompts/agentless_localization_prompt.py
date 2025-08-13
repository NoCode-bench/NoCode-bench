obtain_relevant_files_prompt = """
Please look through the following changed doc contents of GitHub repository and Repository structure and provide a list of files that one would need to edit to adding the new features.

### Changed Doc Contents ###
{problem_statement}

###

### Repository Structure ###
{structure}

###

Please only provide the full path and return at most 5 files.
The returned files should be separated by new lines ordered by most to least important and wrapped with ```
For example:
```
file1.py
file2.py
```
"""

obtain_irrelevant_files_prompt = """
Please look through the following changed doc contents of GitHub repository and Repository structure and provide a list of folders that are irrelevant to adding the new features.
Note that irrelevant folders are those that do not need to be modified and are safe to ignored when trying to solve this problem.

### Changed Doc Contents ###
{problem_statement}

###

### Repository Structure ###
{structure}

###

Please only provide the full path.
Remember that any subfolders will be considered as irrelevant if you provide the parent folder.
Please ensure that the provided irrelevant folders do not include any important files needed to add the new features
The returned folders should be separated by new lines and wrapped with ```
For example:
```
folder1/
folder2/folder3/
folder4/folder5/
```
"""

file_content_template = """
### File: {file_name} ###
{file_content}
"""
file_content_in_block_template = """
### File: {file_name} ###
```python
{file_content}
```
"""

obtain_relevant_code_combine_top_n_prompt = """
Please review the following changed doc contents of GitHub repository and relevant files, and provide a set of locations that need to be edited to add the new features.
The locations can be specified as class names, function or method names, or exact line numbers that require modification.

### Changed Doc Contents ###
{problem_statement}

###
{file_contents}

###

Please provide the class name, function or method name, or the exact line numbers that need to be edited.
The possible location outputs should be either "class", "function" or "line".

### Examples:
```
full_path1/file1.py
line: 10
class: MyClass1
line: 51

full_path2/file2.py
function: MyClass2.my_method
line: 12

full_path3/file3.py
function: my_function
line: 24
line: 156
```

Return just the location(s) wrapped with ```.
"""

obtain_relevant_code_combine_top_n_no_line_number_prompt = """
Please review the following changed doc contents of GitHub repository and relevant files, and provide a set of locations that need to be edited to add the new features.
The locations can be specified as class, method, or function names that require modification.

### Changed Doc Contents ###
{problem_statement}

###
{file_contents}

###

Please provide the class, method, or function names that need to be edited.
### Examples:
```
full_path1/file1.py
function: my_function1
class: MyClass1

full_path2/file2.py
function: MyClass2.my_method
class: MyClass3

full_path3/file3.py
function: my_function2
```

Return just the location(s) wrapped with ```.
"""
obtain_relevant_functions_and_vars_from_compressed_files_prompt_more = """
Please look through the following changed doc contents of GitHub repository and the Skeleton of Relevant Files.
Identify all locations that need inspection or editing to add the new features, including directly related areas as well as any potentially related global variables, functions, and classes.
For each location you provide, either give the name of the class, the name of a method in a class, the name of a function, or the name of a global variable.

### Changed Doc Contents ###
{problem_statement}

### Skeleton of Relevant Files ###
{file_contents}

###

Please provide the complete set of locations as either a class name, a function name, or a variable name.
Note that if you include a class, you do not need to list its specific methods.
You can include either the entire class or don't include the class name and instead include specific methods in the class.
### Examples:
```
full_path1/file1.py
function: my_function_1
class: MyClass1
function: MyClass2.my_method

full_path2/file2.py
variable: my_var
function: MyClass3.my_method

full_path3/file3.py
function: my_function_2
function: my_function_3
function: MyClass4.my_method_1
class: MyClass5
```

Return just the locations wrapped with ```.
"""

obtain_relevant_functions_and_vars_from_raw_files_prompt = """
Please look through the following changed doc contents of GitHub repository and Relevant Files.
Identify all locations that need inspection or editing to add the new features, including directly related areas as well as any potentially related global variables, functions, and classes.
For each location you provide, either give the name of the class, the name of a method in a class, the name of a function, or the name of a global variable.

### Changed Doc Contents ###
{problem_statement}

### Relevant Files ###
{file_contents}

###

Please provide the complete set of locations as either a class name, a function name, or a variable name.
Note that if you include a class, you do not need to list its specific methods.
You can include either the entire class or don't include the class name and instead include specific methods in the class.
### Examples:
```
full_path1/file1.py
function: my_function_1
class: MyClass1
function: MyClass2.my_method

full_path2/file2.py
variable: my_var
function: MyClass3.my_method

full_path3/file3.py
function: my_function_2
function: my_function_3
function: MyClass4.my_method_1
class: MyClass5
```

Return just the locations wrapped with ```.
"""