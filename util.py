import json
import asyncio
import gzip
import asyncgpt
import re
import ast
import sqlite3
import kg_api
import time

async def get_response(index, prompt, bot, setting={}):
    if 'temperature' in setting:
        temperature = setting['temperature']
    else:
        temperature = 0

    final_prompt = setting['instruction_prompt'] + prompt
    message = [{"role": "user", "content": final_prompt}]

    completion = await bot.chat_complete(message, model=setting['model'], temperature=temperature)
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    res = {'pid': index,
           'model': setting['model'],
           'metadata': ds1000[index]['metadata'],
           'temperature': temperature,
           'prompt': final_prompt,
           'completion': completion,
           'message': message,
           'response': completion['choices'][0]['message']['content']
           }
    return res

async def openai_model_repair(id_prompt_list, setting):
    # res_dic = {}
    if 'deepseek' in setting['model']:
        with open('openai_info/deepseek_info.json', 'r') as f:
            info_dic = json.load(f)
    elif 'codestral' in setting['model']:
        with open('openai_info/codestral_info.json', 'r') as f:
            info_dic = json.load(f)
    else:
        with open('openai_info/gpt_info.json', 'r') as f:
            info_dic = json.load(f)

    bot = asyncgpt.AsyncGPT(api_key=info_dic['api_key'], organization=info_dic['organization'], model=setting['model'])
    prompt_list = [get_response(id, prompt, bot, setting) for id, prompt in id_prompt_list]
    res_list = await asyncio.gather(*prompt_list)
    return res_list



async def get_response_conversation(index, message, bot, setting={}):
    # code repair
    if 'temperature' in setting:
        temperature = setting['temperature']
    else:
        temperature = 0
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    try:
        completion = await bot.chat_complete(message, model=setting['model'], temperature=temperature)
        print(completion)
    except Exception as e:
        print(e)
        res = {'pid': index,
               'model': setting['model'],
               'metadata': ds1000[index]['metadata'],
               'temperature': temperature,
               'prompt': message[-1]['content'],
               'completion': {},
               'message': message,
               'response': ''
               }
        return res
    if "choices" in completion:
        res = {'pid': index,
               'model': setting['model'],
               'metadata': ds1000[index]['metadata'],
               'temperature': temperature,
               'prompt': message[-1]['content'],
               'completion': completion,
               'message': message,
               'response': completion['choices'][0]['message']['content']
               }
    else:
        res = {'pid': index,
               'model': setting['model'],
               'metadata': ds1000[index]['metadata'],
               'temperature': temperature,
               'prompt': message[-1]['content'],
               'completion': completion,
               'message': message,
               'response': ''
               }
    return res


async def openai_model_conversation(id_message_list, setting):
    # code repair
    if 'deepseek' in setting['model']:
        with open('openai_info/deepseek_info.json', 'r') as f:
            info_dic = json.load(f)
    elif 'codestral' in setting['model']:
        with open('openai_info/codestral_info.json', 'r') as f:
            info_dic = json.load(f)
    else:
        with open('openai_info/gpt_info.json', 'r') as f:
            info_dic = json.load(f)
    # client = OpenAI(
    #     organization=info_dic['organization'],
    #     api_key=info_dic['api_key']
    # )
    # response_list = description_2_code(client, prompt)

    # file_list = [str(i) for i in range(30)]
    bot = asyncgpt.AsyncGPT(api_key=info_dic['api_key'], organization=info_dic['organization'], model=setting['model'])
    prompt_list = [get_response_conversation(id, message, bot, setting)
                   for id, message in id_message_list]
    res_list = await asyncio.gather(*prompt_list)
    return res_list


def extract_entity_from_std_err(std_err):
    error_info_dic = {
        'error': {},
        'error_location': [],
        # 'std_err': std_err,
    }
    error_pattern = r'(.*?Error)\s*:\s*(.*?)$'
    error_location_pattern = r'File\s*"(.*?)".*?line\s*(\d+).*?in\s*(.*?)$'
    error_location_pattern_1 = r'File\s*"(.*?)".*?line\s*(\d+).*?$'
    for line in std_err.split('\n'):
        error_match = re.findall(error_pattern, line)
        error_location_match = re.findall(error_location_pattern, line)
        error_location_match_1 = re.findall(error_location_pattern_1, line)
        if error_match:
            # print('[error]', line)
            # error_type, error_info
            error_info_dic['error']['type'] = error_match[0][0]
            error_info_dic['error']['explanation'] = error_match[0][1]
            # print(error_match[0][0], error_match[0][1])

        if error_location_match:
            # print('[error_location]', line)
            # file_path, line_no
            error_info_dic['error_location'].append(
                {
                    'file_path': error_location_match[0][0],
                    'line_no': int(error_location_match[0][1]),
                    'error_function_name': error_location_match[0][2]
                }
            )
        elif error_location_match_1:
            error_info_dic['error_location'].append(
                {
                    'file_path': error_location_match_1[0][0],
                    'line_no': int(error_location_match_1[0][1]),
                    'error_function_name': ''
                }
            )
            # print(error_location_match[0][0], error_location_match[0][1], error_location_match[0][2])
    return error_info_dic


def error_line_localization(code_context, solution, error_info_dic):
    exec_environment = {}
    # print(solution)
    # Execute the script within the defined scope
    exec(code_context, {}, exec_environment)
    exec_context = exec_environment['exec_context']
    # print(exec_context)
    code = exec_context.replace("[insert]", solution)
    error_line_no = -1
    for location in error_info_dic['error_location']:
        if location['file_path'] == '<string>':
            error_line_no = location['line_no'] - 1
            break
    # print(error_line_no)
    # print(error_line_no)
    # print(code)
    if error_line_no != -1:
        return code.split('\n')[error_line_no]
    else:
        return


def check_whether_error_related_library(error_info_dic, library_name):
    res = False
    for error_location in error_info_dic['error_location']:
        if library_name.lower() in error_location['file_path'].lower():
            res = True
            break
    return res


def build_SPARQL_query(function_name, library_name):
    query = """
    SELECT ?subject ?predicate ?object WHERE {
        ?subject ?predicate ?object .
        FILTER(REGEX(STR(?subject), "/%s.%s$"))
    }
    """ % (library_name, function_name)

    return query

def build_SPARQL_query_exact(function_name, library_name):
    if 'numpy' in function_name:
        knowledge_graph = 'numpyGraph'
    elif 'pandas' in function_name:
        knowledge_graph = 'pandasGraph'
    elif 'scipy' in function_name:
        knowledge_graph = 'scipyGraph'
    elif 'sklearn' in function_name:
        knowledge_graph = 'sklearnGraph'
    elif 'tensorflow' in function_name:
        knowledge_graph = 'tensorflowGraph'
    elif 'matplotlib' in function_name:
        knowledge_graph = 'matplotlibGraph'
    elif 'pytorch' in function_name or 'torch' in function_name:
        knowledge_graph = 'pytorchGraph'
    else:
        knowledge_graph = library_name.lower() + 'Graph'

    if library_name not in function_name:

        exact_query = f'''SELECT ?subject ?predicate ?object ?predicate1 ?object1
        WHERE {{
          GRAPH <#{knowledge_graph}> {{
            ?subject kg4cg:hasName "{library_name + '.' + function_name}".
            ?subject a kg4cg:Function.
            ?subject ?predicate ?object.
            
            OPTIONAL {{
              ?object a kg4cg:Parameter.
              ?object ?predicate1 ?object1.
            }}
            OPTIONAL {{
              ?object a kg4cg:Return.
              ?object ?predicate1 ?object1.
            }}
          }}
        }}'''
    else:
        exact_query = f'''SELECT ?subject ?predicate ?object ?predicate1 ?object1
        WHERE {{
          GRAPH <#{knowledge_graph}> {{
            ?subject kg4cg:hasName "{function_name}".
            ?subject a kg4cg:Function.
            ?subject ?predicate ?object.
            
            OPTIONAL {{
              ?object a kg4cg:Parameter.
              ?object ?predicate1 ?object1.
            }}
            OPTIONAL {{
              ?object a kg4cg:Return.
              ?object ?predicate1 ?object1.
            }}
          }}
        }}'''

    return exact_query


def build_SPARQL_query_blur(function_name, library_name):
    if 'numpy' in function_name:
        knowledge_graph = 'numpyGraph'
    elif 'pandas' in function_name:
        knowledge_graph = 'pandasGraph'
    elif 'scipy' in function_name:
        knowledge_graph = 'scipyGraph'
    elif 'sklearn' in function_name:
        knowledge_graph = 'sklearnGraph'
    elif 'tensorflow' in function_name:
        knowledge_graph = 'tensorflowGraph'
    elif 'matplotlib' in function_name:
        knowledge_graph = 'matplotlibGraph'
    elif 'pytorch' in function_name or 'torch' in function_name:
        knowledge_graph = 'pytorchGraph'
    else:
        knowledge_graph = library_name.lower() + 'Graph'

    blur_query = f'''SELECT ?subject ?predicate ?object ?predicate1 ?object1
    WHERE {{
      GRAPH <#{knowledge_graph}> {{
        ?subject kg4cg:hasName ?name.
        ?subject a kg4cg:Function.
        ?subject ?predicate ?object.
        FILTER (CONTAINS(LCASE(?name), "{library_name}") &&  STRENDS(LCASE(?name), "{function_name}"))
      	OPTIONAL {{
          ?object a kg4cg:Parameter.
          ?object ?predicate1 ?object1.
      	}}
        OPTIONAL {{
          ?object a kg4cg:Return.
          ?object ?predicate1 ?object1.
        }}
      }}
    }}'''

    return blur_query


def extract_imports(code):
    imports = []
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, alias.asname or alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            for alias in node.names:
                imports.append((f"{module}.{alias.name}", alias.asname or alias.name))
    return imports


def get_library_alains(ds1000, pid):
    library_name_list = ['']
    special_name_list = []
    import_libs = extract_imports(ds1000[pid]['code_context'])
    import_lib_dic = {}
    # print(import_libs)
    for import_lib in import_libs:
        import_lib_dic[import_lib[1]] = import_lib[0]
        if '.' in import_lib[0]:
            special_name_list.append(import_lib)
        # if import_lib[0].lower() == ds1000[pid]['metadata']['library'].lower() or \
        #     import_lib[1].lower() == ds1000[pid]['metadata']['library'].lower():
        if import_lib[0].lower() in ['numpy', 'pandas', 'scipy', 'sklearn', 'pyrotch', 'tensorflow', 'matplotlib'] or \
                'matplotlib' in import_lib[0]:
            library_name_list.append(import_lib[0])
            if import_lib[0] != import_lib[1]:
                library_name_list.append(import_lib[1])
    return library_name_list, special_name_list, import_lib_dic

def error_code_line_analyze(res, ds1000):
    # get library/library alains
    # pid = res['pid']
    library_name_list = ['']
    import_libs = extract_imports(ds1000[res['pid']]['code_context'])
    for import_lib in import_libs:
        if import_lib[0].lower() == ds1000[res['pid']]['metadata']['library'].lower() or \
            import_lib[1].lower() == ds1000[res['pid']]['metadata']['library'].lower():
            library_name_list.append(import_lib[0])
            if import_lib[0] != import_lib[1]:
                library_name_list.append(import_lib[1])

    if res['error_line']:
        function_name_list = get_function_name_in_code_line(res['error_line'], library_name_list)
    else:
        function_name_list = get_function_name_in_code_line(res['generated_code'], library_name_list)

    return function_name_list

def first_occurrence(string, substrings):
    first_index = len(string)
    first_substring = None
    for substring in substrings:
        index = string.find(substring)
        if index != -1 and index < first_index:
            first_index = index
            first_substring = substring
    return first_substring


def get_function_name_in_code_line(code_line, library_name_list, special_name_list, import_lib_dic, only_one=False):
    special_name_dic = {}
    for element in special_name_list:
        special_name_dic[element[1]] = element[0]
    function_name_list = []
    code_line_parts = code_line.split('\n')
    for code_line_part in code_line_parts:
        for library_name in library_name_list:
            # function_name_pattern = r'%s\.(.*?)(?=[\(\),]|$)' % (library_name)
            function_name_pattern = r'%s\.([^\(\)\[,]*?)(?=[\(\)\[,]|$)' % (library_name)
            match_results = re.findall(function_name_pattern, code_line_part)
            if match_results:
                if library_name != '':
                    function_name_list += ['%s.%s' % (import_lib_dic[library_name], x) for x in list(match_results)]
                else:
                    for x in list(match_results):
                        if x in special_name_dic:
                            function_name_list.append(special_name_dic[x])
                        else:
                            function_name_list.append(x)
                    # function_name_list += list(match_results)
    if only_one:
        function_name_list = list(set(function_name_list))
        if first_occurrence(code_line, function_name_list):
            return [first_occurrence(code_line, function_name_list)]
        else:
            return []

    return function_name_list

def get_data_from_codebase(idx):
    db_path = f"dataset/codebase_py.db"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    sql = "select idx, code, code_tokens, comment, modified_comment, repo, is_valid from codebase where idx = ?"
    cur.execute(sql, (idx,))
    res = cur.fetchall()

    cur.close()

    return res[0]


def filter_error_problem(test_res_list, ds1000, small_batch=False):
    res_list = []
    library_dic = {}
    for i, content in enumerate(test_res_list):
        if content['returncode'] != 0:
            error_info_dic = extract_entity_from_std_err(content['stderr'])
            # 1. localize the error line
            error_line = error_line_localization(ds1000[content['pid']]['code_context'], content['generated_code'], error_info_dic)
            # 2. check whether it is related with library
            if error_line:
                content['error_line'] = error_line
                content['error_line'] = error_line
            else:
                content['error_line'] = content['generated_code']
            res_list.append(content)
    return res_list


def search_database(search_result_list):
    return_list = []
    for search_res in search_result_list:
        idx, exemplar, _, _, _, repo, _ = get_data_from_codebase(search_res[0]['idx'])
        return_list.append({
            'idx': search_res[0]['idx'],
            'score': search_res[0]['score'],
            'exemplar': exemplar,
            'repo': repo
        })
    return return_list


def search_database_old(search_result_list):
    return_list = []
    for search_res in search_result_list:
        idx, exemplar, _, _, _, repo, _ = get_data_from_codebase(search_res['idx'])
        return_list.append({
            'idx': search_res['idx'],
            'score': search_res['score'],
            'exemplar': exemplar,
            'repo': repo
        })
    return return_list

def remove_kg_prefix(text):
    rdf_prefix = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    kg4cg_prefix = 'http://w3id.org/kg4cg/vocab#'
    return text.replace(rdf_prefix, '').replace(kg4cg_prefix, '')

def query_type_enrich_res(res, option, ds1000):
    if option['code_search_query_type'] == 'prompt':
        res['query'] = [ds1000[res['pid']]['prompt']]
    elif option['code_search_query_type'] == 'error_line':
        res['query'] = [res['error_line']]
    elif option['code_search_query_type'] == 'full_expression':
        api = kg_api.KgAPI()
        tmp_list = []
        for error_func in list(set(error_code_line_analyze(res, ds1000))):
            sparql_query = build_SPARQL_query_exact(error_func, ds1000[res['pid']]['metadata']['library'].lower())
            query_result = api.query_knowledge_graph(sparql_query).convert()
            for triplet in query_result['results']['bindings']:
                if len(triplet) == 3 and remove_kg_prefix(triplet['predicate']['value']) == 'hasExpression':
                    tmp_list.append(remove_kg_prefix(triplet['object']['value']).replace(
                        '%s.' % (ds1000[res['pid']]['metadata']['library'].lower()), ''))
        res['query'] = tmp_list
    return res

async def openai_model_classifier(ds1000, error_res_list, setting={}):
    # first code generation
    if 'deepseek' in setting['model']:
        with open('openai_info/deepseek_info.json', 'r') as f:
            info_dic = json.load(f)
    elif 'codestral' in setting['model']:
        with open('openai_info/codestral_info.json', 'r') as f:
            info_dic = json.load(f)
    else:
        with open('openai_info/gpt_info.json', 'r') as f:
            info_dic = json.load(f)

    # if 'classifier_type' in setting and setting['classifier_type'] == 'function_suggestion':
    bot = asyncgpt.AsyncGPT(api_key=info_dic['api_key'], organization=info_dic['organization'], model=setting['model'])
    prompt_list = [generate_suggestion(ds1000[p['pid']], p, bot, setting) for p in error_res_list]
    res_list = await asyncio.gather(*prompt_list)
    return res_list

async def generate_suggestion(problem, error_res, bot, setting):
    # Simulate a preprocessing task (e.g., modifying string, making HTTP request)
    # await asyncio.sleep(1)  # Simulating an I/O operation with sleep
    # return f"Processed: {prompt}"
    pid = error_res['pid']
    if 'temperature' in setting:
        temperature = setting['temperature']
    else:
        temperature = 0
    if setting['classifier_type'] == 'function_suggestion':
        topn_suggestion = setting['topn_suggestion']
        if setting['prompt_type'] == 'prompt':
            final_prompt = 'Given the code generation task below:\n'
            final_prompt += problem['prompt'] + '\n'
            final_prompt += ('Please predict the top %s python library functions will be used in generated code. '
                             'The response should only return a list of library function names, where all the name are in type string. '
                             'If the generated code does not need any library function, please only return None. '
                             'If the generated code need less than %s library functions, '
                             'please only return the list with that number of elements. '
                             'The function name should include the library name (not its abbreviation). '
                             'The return format is python list. ' %
                             (topn_suggestion, topn_suggestion))
            # final_prompt = setting['instruction_prompt'] + problem['prompt']
        elif setting['prompt_type'] == 'prompt+code':
            final_prompt = 'Given the code generation task below:\n'
            final_prompt += problem['prompt'] + '\n'
            final_prompt += 'Given the generated incorrect code below:\n'
            final_prompt += error_res['generated_code'] + '\n'
            final_prompt += ('Please suggest the top %s python library functions will be used in generated correct code. '
                             'The response should only return a list of library function names, where all the name are in type string. '
                             'If the generated code does not need any library function, please only return an empty list. '
                             'If the generated code need less than %s library functions, '
                             'please only return the list with that number of elements. '
                             'The function name should include the library name (not its abbreviation). '
                             'The return format is python list. ' %
                             (topn_suggestion, topn_suggestion))
            # final_prompt = setting['instruction_prompt'] + problem['prompt']
        else:
            final_prompt = ''
    elif setting['classifier_type'] == 'direct_classifier':
        final_prompt = 'Given the code generation task below:\n'
        final_prompt += problem['prompt'] + '\n'
        final_prompt += 'Given the generated incorrect code below:\n'
        final_prompt += error_res['generated_code'] + '\n'
        # final_prompt += ('Please judge whether repairing the code need the API function knowledge. '
        #                  'If the generated incorrect code exists incorrect API usage, please return True. '
        #                  'Otherwise, please return False. '
        #                  'The response should only return True or False.')
        final_prompt += ('Please judge whether repairing the code need the API function knowledge. '
                         # 'If the generated incorrect code exists incorrect API usage, please return True. '
                         # 'Otherwise, please return False. '
                         'The response should only return True or False.')
    else:
        final_prompt = ''

    message = [{"role": "user", "content": final_prompt}]
    completion = await bot.chat_complete(message, model=setting['model'], temperature=temperature)
    res = {'pid': pid,
           'metadata': problem['metadata'],
           'temperature': temperature,
           'prompt': final_prompt,
           'completion': completion,
           'message': message,
           'response': completion['choices'][0]['message']['content']
           }
    return res


async def openai_model_explanation(ds1000, error_res_list, setting={}):
    # first code generation
    if 'deepseek' in setting['model']:
        with open('openai_info/deepseek_info.json', 'r') as f:
            info_dic = json.load(f)
    elif 'codestral' in setting['model']:
        with open('openai_info/codestral_info.json', 'r') as f:
            info_dic = json.load(f)
    else:
        with open('openai_info/gpt_info.json', 'r') as f:
            info_dic = json.load(f)


    bot = asyncgpt.AsyncGPT(api_key=info_dic['api_key'], organization=info_dic['organization'], model=setting['model'])
    if 'codestral' in setting['model']:
        res_list = []
        for p in error_res_list:
            tmp_res_list = await asyncio.gather(*[generate_explanation(ds1000[p['pid']], p, bot, setting)])
            print(tmp_res_list[0]['completion'])
            res_list.append(tmp_res_list[0])
            time.sleep(0.2)
    else:
        prompt_list = [generate_explanation(ds1000[p['pid']], p, bot, setting) for p in error_res_list]
        res_list = await asyncio.gather(*prompt_list)
    return res_list

async def generate_explanation(problem, error_res, bot, setting):
    pid = error_res['pid']
    if 'temperature' in setting:
        temperature = setting['temperature']
    else:
        temperature = 0

    if 'explanation_type' in setting:
        explanation_type = 'line_explanation'
    else:
        explanation_type = ''

    if explanation_type == 'line_explanation':
        final_prompt = 'Given the code generation task below:\n'
        final_prompt += problem['prompt'] + '\n'
        final_prompt += 'Given the generated incorrect code below:\n'
        final_prompt += error_res['generated_code'] + '\n'
        final_prompt += 'Explain the generated code line by line\n'
    else:
        final_prompt = 'Given the code generation task below:\n'
        final_prompt += problem['prompt'] + '\n'
        final_prompt += 'Given the generated incorrect code below:\n'
        final_prompt += error_res['generated_code'] + '\n'
        if 'kg_nl' in error_res:
            final_prompt += 'Given the knowledge of functions used in the code below:\n'
            final_prompt += error_res['kg_nl'] + '\n'
        if 'fl_nl' in error_res:
            # final_prompt += 'Given the knowledge of functions used in the code below:\n'
            final_prompt += error_res['fl_nl'] + '\n'


    message = [
        {
            "role": "system",
            "content": "You are a helpful programming assistant. You are helping a user write a program to solve a problem. The user has written some code, but it has some errors and is not passing the tests. You will help the user by giving a detailed but concise textual explanation of what is wrong with the code. You will *not* generate any code, because the user wants to fix the code themselves.",
        },
        {
            "role": "user",
            "content": final_prompt
        }
    ]
    completion = await bot.chat_complete(message, model=setting['model'], temperature=temperature)
    if 'choices' in completion:
        res = {'pid': pid,
               'model': setting['model'],
               'metadata': problem['metadata'],
               'temperature': temperature,
               'prompt': final_prompt,
               'completion': completion,
               'message': message,
               'response': completion['choices'][0]['message']['content']
               }
    else:
        res = {'pid': pid,
               'model': setting['model'],
               'metadata': problem['metadata'],
               'temperature': temperature,
               'prompt': final_prompt,
               'completion': completion,
               'message': message,
               'response': ''
               }
    # print(pid, completion)
    return res


