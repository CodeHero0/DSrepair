import json
from pprint import pprint

import numpy
import pickle
import os
from bs4 import BeautifulSoup
import re
from rdflib import Graph, Namespace, Literal, URIRef
import lxml
from rdflib.namespace import RDF, RDFS
import ast
# numpy version 1.26

def get_dic(tag_list, is_return=False):
    parameter_list = []
    parameter_id = 0
    for x in tag_list:
        if x.text.strip():
            tmp = []
            for child in x.children:
                if child.text.strip():
                    # modification in new version
                    if 'versionmodified added' in str(child):
                        continue
                    elif 'strong' in str(child):
                        tmp.append('parameter:' + child.text)
                        tmp.append('pid:' + str(parameter_id))
                        parameter_id += 1
                    elif hasattr(child, 'attrs') and child.attrs and 'classifier' in child.attrs['class']:
                        tmp.append('type:' + child.text)
                    else:
                        if is_return:
                            if child.find('dt') is not None:
                                tmp.append('parameter:' + 'return_%s' % (parameter_id))
                                tmp.append('pid:' + str(parameter_id))
                                parameter_id += 1
                                tmp.append('type:' + child.text)
                            else:
                                tmp.append(child.text)
                        else:
                            tmp.append(child.text)
            parameter_list.append(tmp)
    parameter_dic = {}
    parameter_indicater = ''
    for parameter in parameter_list:
        for info in parameter:
            if info.startswith('parameter:'):
                parameter_indicater = info.replace('parameter:', '')
                parameter_dic[parameter_indicater] = {}
            elif parameter_indicater and info.startswith('type'):
                parameter_dic[parameter_indicater]['type'] = info.replace('type:', '')
            elif parameter_indicater and info.startswith('pid:'):
                parameter_dic[parameter_indicater]['pid'] = info.replace('pid:', '')
            else:
                if parameter_indicater and 'explanation' not in parameter_dic[parameter_indicater]:
                    parameter_dic[parameter_indicater]['explanation'] = info
                else:
                    parameter_dic[parameter_indicater]['explanation'] += '\n' + info

    # elimiate None
    for key in parameter_dic:
        if key == 'None':
            parameter_dic.pop(key)
    return parameter_dic


def select_object_type(soup):
    object_type = ''
    object_type_list = ['py attribute', 'py function', 'py data', 'py method', 'py class', 'py exception', 'py property']
    for object_type in object_type_list:
        if soup.find(class_=object_type):
            return object_type
    return object_type

def remove_prefix(s, prefix):
    if s.startswith(prefix):
        # Remove "Notes" and any following space
        return s.replace(prefix, '', 1).lstrip()
    return s

def get_file_classify(html_path):
    file_classify = {}
    entries = os.listdir(html_path)
    html_files = [entry for entry in entries if os.path.isfile(os.path.join(html_path, entry))]
    pass_file_list = ['numpy.lib.arraysetops.html', 'numpy.lib.format.html']
    for html_file in html_files:
        # distutils is deprecated
        # the two files in pass_file_list are content webpage
        if 'numpy.distutils' in html_file or html_file in pass_file_list:
            continue
        # print(html_path + html_file)

        with open(html_path + html_file, encoding='utf-8') as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, 'lxml')
        # get the article
        article_element = soup.find('article', class_='bd-article')
        object_type = select_object_type(soup)
        if object_type not in file_classify:
            file_classify[object_type] = [html_file]
        else:
            file_classify[object_type].append(html_file)
    return file_classify


def add_triplet_based_on_name(obj_name, kg, namespace):
    # TODO: finish this function
    pass


def find_value(tree, variable_name):
    # Function to find the value of a variable
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    if isinstance(node.value, ast.List):
                        return [element.value for element in node.value.elts]


def find_specific_variable_assignments(node, variable_name):
    assignments = []
    for sub_node in ast.walk(node):
        if isinstance(sub_node, ast.Assign):
            for target in sub_node.targets:
                # Check if the target is the variable we are looking for
                if isinstance(target, ast.Name) and target.id == variable_name:
                    value = ast.unparse(sub_node.value)
                    assignment = f"{variable_name} = {value}"
                    assignments.append(assignment)
                elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                    # Check if the variable is part of a tuple or list unpacking
                    for element in target.elts:
                        if isinstance(element, ast.Name) and element.id == variable_name:
                            value = ast.unparse(sub_node.value)
                            assignment = f"{ast.unparse(target)} = {value}"
                            assignments.append(assignment)
    return assignments

def split_examples(docstring, function_name):
    example_list = []

    for example in docstring.split('\n\n'):
        if function_name.split('.')[-1] in example:
            example_list.append(example)
    return example_list

def docstring_analysis(docstring, function_name):
    if not docstring:
        return {}
    keyword_list = ['Parameters', 'Returns', 'Examples', 'See Also']
    split_sign = []
    for keyword in keyword_list:
        match_res = re.findall(r'%s\s*\n\s*\-*' % (keyword), docstring)
        if match_res:
            split_sign.append(match_res[0])
    pattern = f"({'|'.join(split_sign)})"
    split_text = re.split(pattern, docstring)
    key = 'explanation'
    docstring_dic = {}
    for text in split_text:
        if text in split_sign:
            key = text.replace('-', '').strip().lower()
            # print(key)
        else:
            if key not in docstring_dic:
                docstring_dic[key] = text
            else:
                docstring_dic[key] += text

    # refine the docstring_dic
    parameter_dic = {}
    return_dic = {}
    examples = []
    for key in docstring_dic:
        # print(key)
        if key == 'parameters':
            parameter_dic = get_parameter_dic_from_docstring(docstring_dic[key])
        elif key == 'returns':
            return_dic = get_parameter_dic_from_docstring(docstring_dic[key])
        elif key == 'examples':
            examples = split_examples(docstring_dic[key], function_name)
        else:
            text_list = docstring_dic[key].split('\n')
            docstring_dic[key] = ' '.join([i.replace('\n','').strip() for i in text_list if i.replace('\n','').strip()])

    docstring_dic['parameter_dic'] = parameter_dic
    docstring_dic['return_dic'] = return_dic
    docstring_dic['examples'] = examples
    return docstring_dic

def get_parameter_dic_from_docstring(docstring_parameter):
    parameter_dic = {}
    parameter_pattern = r'\s*(.*?)\s*:\s*'
    parameter = ''
    pid = 0
    for line in docstring_parameter.split('\n'):
        parameter_match_res = re.findall(parameter_pattern, line)
        if parameter_match_res:
            parameter = parameter_match_res[-1]
            parameter_dic[parameter] = {
                'type': re.sub(parameter_pattern, '', line).strip(),
                'explanation': '',
                'pid': str(pid)
            }
            pid += 1
        else:
            if parameter:
                parameter_dic[parameter]['explanation'] += line.strip()

    return parameter_dic

def decorator_analysis(decorator_list, parsed_code):
    # TODO: maybe need more pattern?
    pattern_0 = r'set_module\(\'(.*?)\'\)'
    pattern_1 = r'module=\'(.*?)\''
    for decorator in decorator_list:
        if 'set_module' in decorator:
            match_res = re.findall(pattern_0, decorator)
            if match_res:
                return match_res[0]
        # elif 'array_function_dispatch' in decorator:
        else:
            match_res = re.findall(pattern_1, decorator)
            if match_res:
                return match_res[0]
            variable_name = decorator.split('(')[0]

            # print(variable_name)
            # assignment_list = find_specific_variable_assignments(parsed_code, 'array_function_dispatch')
            assignment_list = find_specific_variable_assignments(parsed_code, variable_name)
            if assignment_list:
                match_res = re.findall(pattern_1, assignment_list[-1])
                if match_res:
                    return match_res[0]
    return ''

def get_decorators(node):
    return [ast.unparse(decorator) for decorator in node.decorator_list]

def get_docstring(node):
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
        return node.body[0].value.s

def get_function_head(node):
    """Return the function head given a function definition node."""
    if not isinstance(node, ast.FunctionDef):
        return "Not a function definition node"

    # function_head = f"def {node.name}("
    function_head = f"{node.name}("
    args = [arg.arg for arg in node.args.args]
    # Handling default values for arguments
    defaults = [ast.literal_eval(d) for d in node.args.defaults]
    defaults = ["'{}'".format(d) if isinstance(d, str) else str(d) for d in defaults]

    # Combine args and defaults
    default_index = len(args) - len(defaults)
    for i, arg in enumerate(args):
        if i >= default_index:
            function_head += f"{arg}={defaults[i - default_index]}, "
        else:
            function_head += f"{arg}, "

    # Handle *args and **kwargs
    if node.args.vararg:
        function_head += f"*{node.args.vararg.arg}, "
    if node.args.kwarg:
        function_head += f"**{node.args.kwarg.arg}, "

    # Remove trailing comma and space, then close parenthesis
    function_head = function_head.rstrip(", ") + ")"
    return function_head

def get_classes_functions_decorators(node, res_dic, all_objects=[], class_name=None, flag=False):
    if isinstance(node, ast.ClassDef):
        decorators = get_decorators(node)
        # print(f"Class: {node.name}, Decorators: {decorators}")
        for item in node.body:
            if node.name in all_objects:
                res_dic[node.name] = {
                    'decorator': decorators,
                    'docstring': get_docstring(node),
                    'object_type': 'py class'
                }
                get_classes_functions_decorators(item, res_dic, all_objects, class_name=node.name, flag=True)
            else:
                get_classes_functions_decorators(item, res_dic, all_objects, class_name=node.name, flag=False)
    elif isinstance(node, ast.FunctionDef):
        # context = f"inside class {class_name}" if class_name else "at global level"
        decorators = get_decorators(node)
        if class_name:
            key = class_name + '.' + node.name
        else:
            key = node.name
        if flag == True:
            res_dic[key] = {
                'decorator': res_dic[class_name]['decorator'] + decorators,
                'docstring': get_docstring(node),
                'function_head': get_function_head(node),
                'class': class_name,
                'object_type': 'py method'
            }
        else:
            if node.name in all_objects:
                res_dic[key] = {
                    'decorator': decorators,
                    'docstring': get_docstring(node),
                    'function_head': get_function_head(node),
                    'class': class_name,
                    'object_type': 'py function'
                }
        # print(f"    Function: {node.name}, Context: {context}, Decorators: {decorators}")


def reshape_dic(class_func_dic):

    element_dic_list = []

    for key in class_func_dic:
        element_dic = {}
        if 'function_head' in class_func_dic[key] and class_func_dic[key]['function_head']:
            object = class_func_dic[key]['prefix'] + class_func_dic[key]['function_head']
        else:
            object = class_func_dic[key]['prefix'] + key
        explanation = ''
        examples = ''
        parameter_dic = {}
        return_dic = {}
        try:
            explanation = class_func_dic[key]['docstring_dic']['explanation']
        except:
            pass
        try:
            parameter_dic = class_func_dic[key]['docstring_dic']['parameter_dic']
        except:
            pass
        try:
            return_dic = class_func_dic[key]['docstring_dic']['return_dic']
        except:
            pass
        try:
            examples = class_func_dic[key]['docstring_dic']['examples']
        except:
            pass
        element_dic['object'] = {
            'name': class_func_dic[key]['prefix'] + key,
            'full_expression': object,
            'explanation': explanation,
            'object_type': class_func_dic[key]['object_type']
        }
        element_dic['parameters'] = parameter_dic
        element_dic['return'] = return_dic
        # element_dic['note'] = Notes
        element_dic['examples'] = examples
        element_dic_list.append(element_dic)

    return element_dic_list

def get_element_from_code(code_file):
    element_dic = {}
    with open(code_file, 'r') as f:
        code = f.read()
    try:
        parsed_code = ast.parse(code)
    except:
        return []

    all_objects = []
    if '__all__' in code:
        all_objects = find_value(parsed_code, '__all__')

    if not all_objects:
        return element_dic

    class_func_dic = {}
    # iterate all the class and function in the code file
    for node in parsed_code.body:
        try:
            get_classes_functions_decorators(node, class_func_dic, all_objects)
        except:
            continue
    # filter private functions/classes, if the node's name startswith '_'
    pop_key_list = []
    for key in class_func_dic:
        if key.split('.')[-1].startswith('_'):
            pop_key_list.append(key)
    for key in pop_key_list:
        class_func_dic.pop(key)


    for key in class_func_dic:
        # decorator analysis
        pre_fix = decorator_analysis(class_func_dic[key]['decorator'], parsed_code)
        if pre_fix:
            class_func_dic[key]['prefix'] = pre_fix + '.'
        else:
            class_func_dic[key]['prefix'] = ''
        # docstring analysis
        docstring_dic = docstring_analysis(class_func_dic[key]['docstring'], key)
        # print(key)
        # print(docstring_dic)
        class_func_dic[key]['docstring_dic'] = docstring_dic


    # reshape the dic
    element_dic_list = reshape_dic(class_func_dic)

    return element_dic_list

def get_element_from_html_old_version(html_file):
    element_dic = {}
    with open(html_file, encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'lxml')

    # get the article
    article_element = soup.find('article', class_='bd-article')
    if not article_element:
        print('page not available!')
        return
    object_type = select_object_type(soup)
    if not object_type:
        print('Object type not found!')
        return
    # function name
    # object_name = article_element.h1.text.strip()
    object_name = article_element.h1.text.strip()
    if object_name.endswith('#'):
        object_name = object_name[:-1]
    # function
    object = article_element.find(class_='sig sig-object py').text.replace('[source]', '').strip()
    if object.endswith('#'):
        object = object[:-1]
    object_explanation = ''
    try:
        explanation_list = article_element.find(class_=object_type).dd.find_all('p', recursive=False)
        for explanation in explanation_list:
            # print('$$' + explanation.text.replace('\n', ' ').strip())
            content = explanation.text.replace('\n', ' ').strip()
            if content.startswith('See also') or \
                content.startswith('Notes') or \
                content.startswith('Examples') or \
                'versionmodified added' in explanation.string:
                break
            object_explanation += explanation.text.replace('\n', ' ').strip() + '\n'
        # object_explanation = article_element.find(class_=object_type).dd.p.text
    except:
        pass
    object_explanation = object_explanation.strip()
    # print('function explanation: ' + function_explanation.text.strip())
    parameter_dic = {}
    return_dic = {}

    # input parameters
    try:
        parameter_dic = get_dic(article_element.find(class_=object_type).dd.\
                    find(class_=re.compile(r'field-list')).\
                    find_all(class_='field-odd')[-1].dl.children)
    except:
        # print('Do not have parameters or error!')
        pass
    # return
    try:
        return_dic = get_dic(article_element.find(class_=object_type).dd.\
                find(class_=re.compile(r'field-list')).\
                find_all(class_='field-even')[-1].dl.children, is_return=True)
    except:
        # print('Do not have return or error!')
        pass

    # Notes
    Notes = ''
    Notes_flag = False
    try:
        for x in list(article_element.find(class_=object_type).dd.find_all('p')):
            if 'Notes' in str(x) and x.attrs and 'rubric' in x.attrs['class']:
                Notes_flag = True
            if 'Examples' in str(x) and x.attrs and 'rubric' in x.attrs['class']:
                Notes_flag = False
            if Notes_flag:
                Notes += remove_prefix(x.text.strip(), 'Notes')
    except:
        pass

    # Examples (code)
    Examples = []
    try:
        for example in article_element.find_all(class_='doctest highlight-default notranslate'):
            Examples.append(example.text.strip())
    except:
        pass

    if object_type == 'py data':
        object_type = 'py function'
    element_dic['object'] = {
        'name': object_name,
        'full_expression': object,
        'explanation': object_explanation,
        'object_type': object_type.replace('py ', '')
    }
    element_dic['parameters'] = parameter_dic
    element_dic['return'] = return_dic
    element_dic['note'] = Notes
    element_dic['examples'] = Examples
    return element_dic

def get_element_from_html(html_file):
    with open(html_file, encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'lxml')

    # get the article
    article_element = soup.find('article', class_='bd-article')
    if not article_element:
        print('page not available!')
        return None, None
    soup_object_list = get_object_type_new(article_element)
    entailment_relationships = []
    if len(soup_object_list) >= 1:
        entailment_relationships = relation_analyze(soup_object_list)

    # for the first object, the rest objects need to add suffix
    object_name_prefix = article_element.h1.text.strip()
    if object_name_prefix.endswith('#'):
        object_name_prefix = object_name_prefix[:-1]
    element_dic_list = []
    for index, soup_object in enumerate(soup_object_list):
        element_dic = {}
        # object type
        object_type = ' '.join(soup_object.get('class'))
        # object name
        if index in [x[1] for x in entailment_relationships]:
            # only need the name without parameters
            suffix_name = ''
            if soup_object.dt.find(class_='sig-name'):
                tmp = soup_object.dt.find(class_='sig-name').text
                # if object_type.split(' ')[-1] in tmp:
                #     tmp = tmp.replace(object_type.split()[-1], '').strip()
                suffix_name += '.' + tmp
            object_name = (object_name_prefix + suffix_name).strip()
        else:
            object_name = object_name_prefix.strip()
        if '[source]' in object_name:
            object_name = object_name.replace('[source]', '')
        if object_name.endswith('#'):
            object_name = object_name[:-1]

        # object full expression
        object = soup_object.find(class_='sig sig-object py').text.replace('[source]', '').strip()
        if object.endswith('#'):
            object = object[:-1]
        if object_type.split(' ')[-1] in object:
            object = object.replace(object_type.split()[-1], '').strip()

        # object explanation
        object_explanation = ''
        try:
            explanation_list = soup_object.dd.find_all('p', recursive=False)
            # print(explanation_list)
            for explanation in explanation_list:
                # print('$$' + explanation.text.replace('\n', ' ').strip())
                content = explanation.text.replace('\n', ' ').strip()
                if content.startswith('See also') or \
                        content.startswith('Notes') or \
                        content.startswith('Examples') or \
                        'Methods' in explanation.string:
                    break
                object_explanation += explanation.text.replace('\n', ' ').strip() + '\n'
        except:
            pass
        object_explanation = object_explanation.strip()

        parameter_dic = {}
        return_dic = {}
        try:
            parameter_dic = get_dic(soup_object.dd. \
                                    find(class_=re.compile(r'field-list')). \
                                    find_all(class_='field-odd')[-1].dl.children)
        except:
            pass

        try:
            return_dic = get_dic(soup_object.dd.\
                    find(class_=re.compile(r'field-list')).\
                    find_all(class_='field-even')[-1].dl.children, is_return=True)
        except:
            # print('Do not have return or error!')
            pass

        # Notes
        Notes = ''
        Notes_flag = False
        try:
            for x in list(soup_object.dd.find_all('p')):
                if 'Notes' in str(x) and x.attrs and 'rubric' in x.attrs['class']:
                    Notes_flag = True
                if 'Examples' in str(x) and x.attrs and 'rubric' in x.attrs['class']:
                    Notes_flag = False
                if Notes_flag:
                    Notes += remove_prefix(x.text.strip(), 'Notes')
        except:
            pass


        # Examples (code)
        # no examples for matplotlib for now
        # TODO: add examples for matplotlib
        Examples = []
        # try:
        #     for example in soup_object.find_all(class_='doctest highlight-default notranslate'):
        #         Examples.append(example.text.strip())
        # except:
        #     pass

        if object_type == 'py data':
            object_type = 'py function'
        element_dic['object'] = {
            'name': object_name,
            'full_expression': object,
            'explanation': object_explanation,
            'object_type': object_type.replace('py ', ''),
            'url': html_file
        }
        if parameter_dic:
            element_dic['parameters'] = parameter_dic
        if return_dic:
            element_dic['return'] = return_dic
        if Notes:
            element_dic['note'] = Notes
        if Examples:
            element_dic['examples'] = Examples
        element_dic_list.append(element_dic)
    return element_dic_list, entailment_relationships

def entailment_relationship2triplet(entailment_relations, element_dic_list, kg, namespace_URI):
    namespace = Namespace(namespace_URI)
    for entailment in entailment_relations:
        parent = element_dic_list[entailment[0]]['object']
        child = element_dic_list[entailment[1]]['object']
        kg.add((namespace[parent['name']],
                namespace['has_py%s' % (child['object_type'])],
                namespace[child['name']]))
        # print(parent['name'], 'has_py%s' % (child['object_type']), child['name'])

def get_object_type_new(soup):
    matching_object_list = []
    object_type_list = ['py attribute', 'py function', 'py data', 'py method', 'py class', 'py exception', 'py property']
    for tag in soup.find_all(True):
        if tag.get('class') and set(object_type_list).intersection({' '.join(tag.get('class'))}):
            matching_object_list.append(tag)
    return matching_object_list

def object_name_clean(object_name):
    modified_flag = True
    while modified_flag:
        if '[source]' in object_name:
            object_name = object_name.replace('[source]', '')
        elif object_name.endswith('#'):
            object_name = object_name[:-1]
        elif object_name.endswith('¶'):
            object_name = object_name[:-1]
        else:
            modified_flag = False
    return object_name

def relation_analyze(object_list):
    entailment_relationships = []
    for i, obj_i in enumerate(object_list):
        for j, obj_j in enumerate(object_list):
            if j<=i:
                continue
            if str(obj_j) in str(obj_i):
                # obj_i is obj_j's parent
                entailment_relationships.append((i, j))
    return entailment_relationships

def transfer_element_dic_2_triplet(element_dic, kg, namespace_URI):
    namespace = Namespace(namespace_URI)

    # object
    object_dic = element_dic['object']
    kg.add((namespace['.'.join(object_dic['name'].split('.')[:-1])],
            namespace['has_%s' % (object_dic['object_type'].replace(' ',''))],
            namespace[object_dic['name']]))

    kg.add((namespace[object_dic['name']],
            namespace['has_explanation'],
            Literal(object_dic['explanation'])))
    kg.add((namespace[object_dic['name']],
            namespace['has_object_expression'],
            Literal(object_dic['full_expression'])))
    kg.add((namespace[object_dic['name']],
            namespace['is_a'],
            Literal(object_dic['object_type'])))

    # note
    if 'note' in element_dic:
        kg.add((namespace[object_dic['name']],
                namespace['has_note'],
                Literal(element_dic['note'])))
    # examples
    if 'examples' in element_dic:
        examples = element_dic['examples']
        for example in examples:
            kg.add((namespace[object_dic['name']],
                    namespace['has_example'],
                    Literal(example)))

    # parameter
    if 'parameters' in element_dic:
        parameter_namespace = Namespace(namespace_URI + object_dic['name'] + '/')
        parameter_dic = element_dic['parameters']
        for parameter in parameter_dic:
            kg.add((namespace[object_dic['name']],
                    namespace['has_parameter'],
                    parameter_namespace['parameter_' + parameter_dic[parameter]['pid']]))

            for attribute in parameter_dic[parameter]:
                if attribute == 'pid':
                    kg.add((parameter_namespace['parameter_' + parameter_dic[parameter]['pid']],
                            parameter_namespace['has_name'],
                            Literal(parameter)))
                kg.add((parameter_namespace['parameter_' + parameter_dic[parameter]['pid']],
                        parameter_namespace['has_' + attribute],
                        Literal(parameter_dic[parameter][attribute])))

    # return
    if 'return' in element_dic:
        parameter_namespace = Namespace(namespace_URI + object_dic['name'] + '/')
        parameter_dic = element_dic['return']
        for parameter in parameter_dic:

            kg.add((namespace[object_dic['name']],
                    namespace['has_return'],
                    parameter_namespace['return_' + parameter_dic[parameter]['pid']]))

            for attribute in parameter_dic[parameter]:
                if attribute == 'pid':
                    kg.add((parameter_namespace['return_' + parameter_dic[parameter]['pid']],
                            parameter_namespace['has_name'],
                            Literal(parameter)))
                kg.add((parameter_namespace['return_' + parameter_dic[parameter]['pid']],
                        parameter_namespace['has_' + attribute],
                        Literal(parameter_dic[parameter][attribute])))

    if 'attribute' in element_dic:
        # TODO: finish this logic
        attribute_namespace = Namespace(namespace_URI + object_dic['name'] + '/')
        attribute_dic = element_dic['attribute']
        for attribute in attribute_dic:
            kg.add((namespace[object_dic['name']],
                    namespace['has_pyattribute'],
                    attribute_namespace[attribute]))

            for x in attribute_dic[attribute]:
                if x == 'pid':
                    continue
                kg.add((attribute_namespace[attribute],
                        attribute_namespace['has_' + x],
                        Literal(attribute_dic[attribute][x])))
        pass

def transfer_element_dic_2_triplet_new(library_name, element_dic, kg_api, filter='function_only'):
    # object
    object_dic = element_dic['object']
    if filter == 'function_only':
        if not object_dic['object_type'] in ['method', 'function', 'attribute']:
            return
        # private function not include
        if object_dic['full_expression'].startswith('_'):
            return
        kg_api.add_instance_from_dic(element_dic, library_name)