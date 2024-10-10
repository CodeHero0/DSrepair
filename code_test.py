import gzip
import json
import re
import pprint
import os
import subprocess
import builtins
from util import *
import aiofiles
import difflib

def get_solution(code_list, ind):
    return code_list[ind]['code']

def test_code(pid, problem_dic, response_dic, ds1000):
    cwd = os.getcwd()
    new_path = 'test_folder/'
    os.chdir(new_path)
    code = response2code(response_dic['response'], ds1000[pid]['prompt'])

    test_program = (
            problem_dic['code_context'] + '\n'
            # + f'code = {repr(get_solution(id))}\n'
            + f'code = {repr(code)}\n'
            + 'test_execution(code)\n'
            + ('test_string(code)\n' if 'test_string(' in problem_dic['code_context'] else '\n')
    )
    test_file = 'test_demo_%s.py' % (pid)
    with open(test_file, 'w') as f:
        f.write(test_program)
    try:
        output = subprocess.run(["python", test_file], capture_output=True, text=True, timeout=120)
    except:
        output = None
    os.chdir(cwd)
    return output, code, test_program


def is_similar(target, string_list, threshold=0.7):
    # Define a helper function to calculate similarity
    def similarity(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio()

    # Check each string in the list
    for string in string_list:
        # Check the whole string first
        if similarity(target, string) >= threshold:
            return True

        # Check all substrings of the current string
        for start in range(len(string)):
            for end in range(start + 1, len(string) + 1):
                substring = string[start:end]
                if similarity(target, substring) >= threshold:
                    return True

    return False


def response2code(response, prompt, stop_sign='</code>\nEND SOLUTION'):
    # extract generated code completion from response
    code_template = re.compile('```.*\n([\s\S]+?)\n```', re.M)
    code_template2 = re.compile('<code>.*\n([\s\S]+?)\n</code>', re.M | re.I)
    match_res = code_template.findall(response)
    match_res2 = code_template2.findall(response)
    if len(match_res) > 0:
        tmp_code = match_res[-1]
    elif len(match_res2) > 0:
        tmp_code = match_res2[-1]
    else:
        tmp_code = response.split(stop_sign)[0]
    # remove the duplicated code that appears once in prompt
    prompt_line_list = prompt.split('A:')[-1].split('\n')
    # prompt_line_list = [i.strip() for i in prompt_line_list]
    variable_names = []
    for line in prompt_line_list:
        if '=' in line:
            if line.split('=')[0].strip() != 'result' and '... #' not in line:
                variable_names.append(line.split('=')[0].strip())
    # print(variable_names)
    # print(prompt_line_list)
    stop_sign_list = stop_sign.split('\n')
    return_code = ''
    assign_flag = False
    for index, line in enumerate(tmp_code.split('\n')):
        if line.split('=')[0].strip() in variable_names:
            continue
        if line.strip().startswith('print('):
            continue
        # # if not assign_flag and '=' in line and line.strip().endswith(','):
        # #     assign_flag = True
        if line.strip().endswith(','):
            assign_flag = True
            continue
        if assign_flag:
            assign_flag = False
            continue
        if (line.strip() not in prompt_line_list) and (line.strip() not in stop_sign_list):
            return_code += line + '\n'
    # for index, line in enumerate(tmp_code.split('\n')):
        # if only_diff:
        #     if line.strip() not in prompt_line_list:
        #         return_code += line.strip() + '\n'
        # else:
        # if (line.strip() not in prompt_line_list) and (line.strip() not in stop_sign_list):
        #     return_code += line + '\n'
    # change the final return with 'result' as variable

    # return_code_line_list = return_code.strip().split('\n')
    # last_line = 'result = ' + return_code_line_list[-1].split('=', 1)[-1]
    # return_code_line_list[-1] = last_line
    # return_code = '\n'.join(return_code_line_list)
    return return_code

def run_first_test(target_file_name):
    with open('intermediate_result/initial_code/' + target_file_name, 'r') as f:
        response_list = json.load(f)
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    output_list = []

    for response_dic in response_list:
        print(response_dic['index'])
        problem_dic = ds1000[response_dic['index']]
        output, code, test_program = test_code(response_dic['index'], problem_dic, response_dic, ds1000)
        output_list.append(output)
        with open('intermediate_result/first_test/' + target_file_name, 'a') as f:
            if output:
                f.write(json.dumps({
                    'args': output.args,
                    'returncode': output.returncode,
                    'stderr': output.stderr,
                    'stdout': output.stdout,
                    'generated_code': code,
                    'test_program': test_program
                }) + '\n')
            else:
                f.write(json.dumps({
                    'args': '',
                    'returncode': 1,
                    'stderr': 'Timeout',
                    'stdout': '',
                    'generated_code': code,
                    'test_program': test_program
                }) + '\n')
        # print(output)
        # break

def load_buildin_errors():
    builtin_errors = []
    for name in dir(builtins):
        obj = getattr(builtins, name)
        # Check if the object is a subclass of BaseException
        if isinstance(obj, type) and issubclass(obj, BaseException):
            if name.endswith('Error'):
                builtin_errors.append(name)
    return builtin_errors


def extract_error_type_from_error_info(error_info):
    last_line = error_info.strip().split('\n')[-1]
    error_type = last_line.split(':')[0]
    return error_type


def enrich_return(target_file, return_flag=False):
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    with open('intermediate_result/initial_code/' + target_file, 'r') as f:
        response_list = json.load(f)
    builtin_errors = load_buildin_errors()
    # enrich first test return list
    index = 0
    output_list = []
    with open('intermediate_result/first_test/' + target_file, 'r') as f:
        for line in f.readlines():
            content = json.loads(line)
            error_info_dic = {}
            error_line = ''
            error_type = ''
            generated_code = response2code(response_list[index]['response'], ds1000[index]['prompt'])
            if content['returncode'] != 0:
                error_type = extract_error_type_from_error_info(content['stderr'])
                if error_type == 'AssertionError':
                    pass
                else:
                    # 2. error localization
                    error_info_dic = extract_entity_from_std_err(content['stderr'])
                    # 3. error function extraction
                    error_line = error_line_localization(ds1000[index]['code_context'], generated_code, error_info_dic)
                    # print('*****error line:\n', error_line)
                    # print(error_info_dic['std_err'])
                    # a = input()
            content['error_info_dic'] = error_info_dic
            content['error_line'] = error_line
            content['error_type'] = error_type
            content['pid'] = index
            content['completion'] = response_list[index]['completion']
            content['message'] = response_list[index]['message']

            index += 1
            output_list.append(content)
    if return_flag:
        return output_list
    with open('intermediate_result/first_test/enriched_' + target_file, 'w') as f:
        for output in output_list:
            f.write(json.dumps(output) + '\n')


# def get_test_code(problem_dic, response_dic, ds1000):
#     code = response2code(response_dic['response'], ds1000[response_dic['pid']]['prompt'])
#     # output_list = []
#     # id = int(problem_dic['metadata']['problem_id'])
#
#     # lib = problem_dic['metadata']['library']
#     test_program = (
#             problem_dic['code_context'] + '\n'
#             # + f'code = {repr(get_solution(id))}\n'
#             + f'code = {repr(code)}\n'
#             + 'test_execution(code)\n'
#             + ('test_string(code)\n' if 'test_string(' in problem_dic['code_context'] else '\n')
#     )
#     return test_program

async def test_single_code_async(response_id, pid, code_context, code, cwd):
    semaphore = asyncio.Semaphore(100)
    async with semaphore:
        if cwd:
            os.chdir(cwd)
            test_dir_0 = 'test_folder_async_0'
            if not os.path.exists(test_dir_0 + '/'):
                os.makedirs(test_dir_0 + '/')
            test_dir = '%s/test_%s' % (test_dir_0, pid)
            if not os.path.exists(test_dir):
                os.makedirs(test_dir)
            os.chdir(test_dir)
        output = {}
        test_program = (
                code_context + '\n'
                + f'code = {repr(code)}\n'
                + 'test_execution(code)\n'
                + ('test_string(code)\n' if 'test_string(' in code_context else '\n')
        )

        test_file = 'test_demo_%s.py' % (pid)

        # Use aiofiles to write the file asynchronously
        async with aiofiles.open(test_file, 'w') as f:
            await f.write(test_program)

        try:
            # Run the subprocess asynchronously
            process = await asyncio.create_subprocess_exec(
                "python", test_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=False,
            )

            # Wait for the process to complete and capture stdout and stderr
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)

            # Decode the outputs from bytes to string
            output['stdout'] = stdout.decode()
            output['stderr'] = stderr.decode()
            output['returncode'] = process.returncode

        except asyncio.TimeoutError:
            output['stdout'] = ''
            output['stderr'] = 'Process timed out'
            output['returncode'] = -1
        # except Exception as e:
        #     output['stdout'] = ''
        #     output['stderr'] = str(e)
        #     output['returncode'] = -1
        # res_list = asyncio.run(run_test_async(test_list))
        if cwd:
            os.chdir(cwd)
        return response_id, pid, output, code, test_program

async def run_test_async(test_list, cwd=''):
    prompt_list = [test_single_code_async(response_id, pid, code_context, code, cwd) for response_id, pid, code_context, code in test_list]
    res_list = await asyncio.gather(*prompt_list)
    return res_list

def test_code_async(response_list, ds1000):
    test_list = []
    final_res_list = []
    cwd = os.getcwd()
    for response_id, response_dic in enumerate(response_list):
        code = response2code(response_dic['response'], ds1000[response_dic['pid']]['prompt'])
        if 'index' in response_dic:
            test_list = []
            test_list.append([response_id, response_dic['index'], ds1000[response_dic['index']]['code_context'], code])
            res_list = asyncio.run(run_test_async(test_list, cwd))
            final_res_list.append(res_list[0])
        else:
            test_list = []
            test_list.append([response_id, response_dic['pid'], ds1000[response_dic['pid']]['code_context'], code])
            res_list = asyncio.run(run_test_async(test_list, cwd))
            final_res_list.append(res_list[0])
    return final_res_list
    #     if 'index' in response_dic:
    #         test_list.append(
    #             [response_id, response_dic['index'], ds1000[response_dic['index']]['code_context'], code])
    #     else:
    #         test_list.append([response_id, response_dic['pid'], ds1000[response_dic['pid']]['code_context'], code])
    # new_path = 'test_folder_async/'
    # os.chdir(new_path)
    # res_list = asyncio.run(run_test_async(test_list))
    # os.chdir(cwd)
    # res_list = asyncio.run(run_test_async(test_list, cwd))
    # return res_list

def library_error_statistic(target_file):
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    builtin_errors = load_buildin_errors()
    first_test_list = enrich_return(target_file, return_flag=True)
    # investigation how serious is library-related error
    error_num = 0
    error_type_dic = {}
    for content in first_test_list:
        if content['returncode'] != 0:
            error_num += 1
            for line in content['stderr'].strip().split('\n'):
                error_type = line.split(':', 1)[0]
                if error_type in builtin_errors:
                    break
            if 'Timeout' in error_type:
                pass
            elif ' ' in error_type:
                print(content['stderr'])
                a = input()
            if error_type not in error_type_dic:
                error_type_dic[error_type] = [content['index']]
            else:
                error_type_dic[error_type].append(content['index'])


    #   1. localize the error line
    #   2. check whether it has library (not enough)
    library_error_count = 0
    for i, content in enumerate(first_test_list):

        if content['returncode'] != 0:
            print(i)
            error_info_dic = extract_entity_from_std_err(content['stderr'])
            # print('*****stderr:', error_info_dic['std_err'])
            # 1. localize the error line
            error_line = error_line_localization(ds1000[content['index']]['code_context'], content['generated_code'], error_info_dic)
            # 2. check whether it is related with library
            if check_whether_error_related_library(error_info_dic, ds1000[content['index']]['metadata']['library']):
                library_error_count += 1
                print(error_info_dic['std_err'])
                print('--------------')
                print(error_line)
                a = input()
            # print('*****error line:\n', error_line)
            # a = input()
    # index = 1
    # test_code = get_test_code(ds1000[index], response_list[index])

def run_test(file, store_folder):
    with open(file, 'r') as f:
        response_list = json.load(f)
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    output_list = test_code_async(response_list, ds1000)
    for response_id, pid, output, code, test_program in output_list:
        with open(store_folder + file.split('/')[-1], 'a') as f:
            if output:
                f.write(json.dumps({
                    'pid': pid,
                    # 'args': output.args,
                    'returncode': output.returncode,
                    'stderr': output.stderr,
                    'stdout': output.stdout,
                    'generated_code': code,
                    'test_program': test_program,
                    'completion': response_list[response_id]['completion'],
                    'message': response_list[response_id]['message'],
                }) + '\n')
            else:
                f.write(json.dumps({
                    'pid': pid,
                    # 'args': '',
                    'returncode': 1,
                    'stderr': 'Timeout',
                    'stdout': '',
                    'generated_code': code,
                    'test_program': test_program
                }) + '\n')


    # for response_dic in response_list:
    #     print('TESTING %s' % response_dic['index'])
    #     problem_dic = ds1000[response_dic['index']]
    #     output, code, test_program = test_code(problem_dic, response_dic)
    #     output_list.append(output)
    #     with open(store_folder + file.split('/')[-1], 'a') as f:
    #         if output:
    #             f.write(json.dumps({
    #                 'pid': response_dic['index'],
    #                 'args': output.args,
    #                 'returncode': output.returncode,
    #                 'stderr': output.stderr,
    #                 'stdout': output.stdout,
    #                 'generated_code': code,
    #                 'test_program': test_program,
    #                 'completion': response_dic['completion'],
    #                 'message': response_dic['message'],
    #             }) + '\n')
    #         else:
    #             f.write(json.dumps({
    #                 'pid': response_dic['index'],
    #                 'args': '',
    #                 'returncode': 1,
    #                 'stderr': 'Timeout',
    #                 'stdout': '',
    #                 'generated_code': code,
    #                 'test_program': test_program
    #             }) + '\n')


def run_test_conversation(response_list, file_path, Done_flag):
    if not os.path.exists(file_path.split('/')[0] + '/repair_test/'):
        os.makedirs(file_path.split('/')[0] + '/repair_test/')
    test_res_file_path = file_path.split('/')[0] + '/repair_test/' + file_path.split('/')[1]
    if Done_flag and os.path.exists(test_res_file_path):
        return test_res_file_path
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    output_list = test_code_async(response_list, ds1000)
    for response_id, pid, output, code, test_program in output_list:
        with open(test_res_file_path, 'a') as f:
            if output:
                f.write(json.dumps({
                    'pid': pid,
                    # 'args': output.args,
                    # 'returncode': output.returncode,
                    # 'stderr': output.stderr,
                    # 'stdout': output.stdout,
                    'returncode': output['returncode'],
                    'stderr': output['stderr'],
                    'stdout': output['stdout'],

                    'generated_code': code,
                    'test_program': test_program,
                    'completion': response_list[response_id]['completion'],
                    'message': response_list[response_id]['message'],
                }) + '\n')
            else:
                f.write(json.dumps({
                    'pid': pid,
                    # 'args': '',
                    'returncode': 1,
                    'stderr': 'Timeout',
                    'stdout': '',
                    'generated_code': code,
                    'test_program': test_program
                }) + '\n')

    # output_list = []
    # for response_dic in response_list:
    #     print('conversation TESTING %s' % response_dic['pid'])
    #     problem_dic = ds1000[response_dic['pid']]
    #     output, code, test_program = test_code(problem_dic, response_dic)
    #     output_list.append(output)
    #     with open(test_res_file_path, 'a') as f:
    #         if output:
    #             f.write(json.dumps({
    #                 'pid': response_dic['pid'],
    #                 'args': output.args,
    #                 'returncode': output.returncode,
    #                 'stderr': output.stderr,
    #                 'stdout': output.stdout,
    #                 'generated_code': code,
    #                 'test_program': test_program,
    #                 'completion': response_dic['completion'],
    #                 'message': response_dic['message'],
    #             }) + '\n')
    #         else:
    #             f.write(json.dumps({
    #                 'pid': response_dic['pid'],
    #                 'args': '',
    #                 'returncode': 1,
    #                 'stderr': 'Timeout',
    #                 'stdout': '',
    #                 'generated_code': code,
    #                 'test_program': test_program,
    #                 'completion': response_dic['completion'],
    #                 'message': response_dic['message'],
    #             }) + '\n')


    return test_res_file_path

def run_repair_test(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            # run_test(file_path, 'intermediate_result/repair_test_stderr/')
            # run_test(file_path, 'intermediate_result/repair_test_code_search/')
            # run_test(file_path, 'intermediate_result/repair_test_stderr+code_search/')
            # run_test(file_path, 'intermediate_result/repair_test_kg/')
            # run_test(file_path, 'intermediate_result/repair_test_stderr+kg_more/')
            run_test(file_path, 'intermediate_result/repair_test_stderr+kg_more+bug/')


# if __name__ == '__main__':
#     target_file = 'ds1000_t_1.json'
    # run_first_test(target_file)
    # enrich_return(target_file)
    # run_repair_test('./intermediate_result/stderr_only/')
    # run_repair_test('./intermediate_result/code_search_repair/')
    # run_repair_test('./intermediate_result/stderr+code_search_repair/')
    # run_repair_test('./intermediate_result/stderr+kg_repair_more/')
    # run_repair_test('./intermediate_result/stderr+kg_repair_more+bug/')
    # pass



    # ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    # with open('intermediate_result/initial_code/' + target_file_name, 'r') as f:
    #     response_list = json.load(f)
    #
    # for i, response in enumerate(response_list):
    #
    #     code = response2code(response['response'], response['prompt'])
    #     print('-----------------')
    #     print(code)
    #     print('++++++++++++++++++++')
    #     exec_environment = {}
    #
    #     exec(ds1000[i]['code_context'], {}, exec_environment)
    #     exec_context = exec_environment['exec_context']
    #
    #     inside_code = exec_context.replace("[insert]", code)
    #     print(inside_code)
    #     a = input()


