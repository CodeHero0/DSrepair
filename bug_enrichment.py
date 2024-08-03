import copy
import numpy as np
import copy
from scipy.stats import rankdata
import json
import gzip
import ast
from pprint import pprint
from util import *
from extract_spoiled_test_case import code_context_2_testcase

np.random.seed(42)

def exec_code(node, global_dict, pid):
    try:
        if pid == 366 and isinstance(node, ast.For):
            exec('%s\n%s' % (ast.unparse(node), 'result = a'), global_dict)
        else:
            exec('%s = %s' % ('result', ast.unparse(node)), global_dict)
    except Exception as e:
        global_dict['error'] = [ast.unparse(node), e]
        # print(e)


def execute_and_explain(node, global_dict, result_dict, pid=0, level=0, print_flag=False):
    indent = "-" * level
    result_dict['node_history'].append([ast.unparse(node), level, type(node)])
    # print(result_dict['node_history'])
    try:
        if isinstance(node, ast.Module):
            if print_flag:
                print(indent + 'Module:' + ast.unparse(node))
            for n in node.body:
                execute_and_explain(n, global_dict, result_dict, pid, level + 1)

        elif isinstance(node, ast.Assign):
            if print_flag:
                print(indent + 'Assign:' + ast.unparse(node))
            # values (='s right)
            execute_and_explain(node.value, global_dict, result_dict, pid, level + 1)
            # targets (='s left)
            for n in node.targets:
                execute_and_explain(n, global_dict, result_dict, pid, level + 1)
            assign_ast = ast.parse(ast.unparse(node), mode='exec')
            compiled_assign = compile(assign_ast, filename="<ast>", mode='exec')
            exec(compiled_assign, global_dict)
        elif isinstance(node, ast.Call):
            if print_flag:
                print(indent + 'Call:' + ast.unparse(node))
            exec_code(node, global_dict, pid)
            if 'result' in global_dict:
                if print_flag:
                    print(global_dict['result'])
                result_dict['ans_dict'] = {
                    'history': copy.deepcopy(result_dict['node_history']),
                    'value': global_dict['result']
                }
                return
            else:
                # args
                for n in node.args:
                    execute_and_explain(n, global_dict, result_dict, pid, level + 1)
                # func
                execute_and_explain(node.func, global_dict, result_dict, pid, level + 1)
        elif isinstance(node, ast.Subscript):
            if print_flag:
                print(indent + 'Subscript:' + ast.unparse(node))
            exec_code(node, global_dict, pid)
            if 'result' in global_dict:
                if print_flag:
                    print(global_dict['result'])
                result_dict['ans_dict'] = {
                    'history': copy.deepcopy(result_dict['node_history']),
                    'value': global_dict['result']
                }
                return
            else:
                # slice
                execute_and_explain(node.slice, global_dict, result_dict, pid, level + 1)
                # value
                execute_and_explain(node.value, global_dict, result_dict, pid, level + 1)

        elif isinstance(node, ast.Tuple):
            if print_flag:
                print(indent + 'Tuple:' + ast.unparse(node))
            exec_code(node, global_dict, pid)
            if 'result' in global_dict:
                if print_flag:
                    print(global_dict['result'])
                result_dict['ans_dict'] = {
                    'history': copy.deepcopy(result_dict['node_history']),
                    'value': global_dict['result']
                }
                return
            else:
                pass
            # dims
            for n in node.dims:
                execute_and_explain(n, global_dict, result_dict, pid, level + 1)
            # elts
            for n in node.elts:
                execute_and_explain(n, global_dict, result_dict, pid, level + 1)
        elif isinstance(node, ast.ListComp):
            if print_flag:
                print(indent + 'ListComp:' + ast.unparse(node))
            exec_code(node, global_dict, pid)
            if 'result' in global_dict:
                if print_flag:
                    print(global_dict['result'])
                result_dict['ans_dict'] = {
                    'history': copy.deepcopy(result_dict['node_history']),
                    'value': global_dict['result']
                }
                return
            else:
                pass
        elif isinstance(node, ast.For):
            if print_flag:
                print(indent + 'For:' + ast.unparse(node))
            exec_code(node, global_dict, pid)
            if 'result' in global_dict:
                if print_flag:
                    print(global_dict['result'])
                result_dict['ans_dict'] = {
                    'history': copy.deepcopy(result_dict['node_history']),
                    'value': global_dict['result']
                }
                return
            else:
                pass
        elif isinstance(node, ast.BinOp):
            if print_flag:
                print(indent + 'BinOp:' + ast.unparse(node))
            exec_code(node, global_dict, pid)
            if 'result' in global_dict:
                if print_flag:
                    print(global_dict['result'])
                result_dict['ans_dict'] = {
                    'history': copy.deepcopy(result_dict['node_history']),
                    'value': global_dict['result']
                }
                return
            else:
                execute_and_explain(node.left, global_dict, result_dict, pid, level + 1)
                execute_and_explain(node.right, global_dict, result_dict, pid, level + 1)
                pass
        elif isinstance(node, ast.Attribute):
            if print_flag:
                print(indent + 'Attribute:' + ast.unparse(node))
            execute_and_explain(node.value, global_dict, result_dict, pid, level + 1)

        elif isinstance(node, ast.Constant):
            if print_flag:
                print(indent + f"Constant: {node.value}")
        elif isinstance(node, ast.FunctionDef):
            if print_flag:
                print(indent + f"FunctionDef: {node.name}")
            function_ast = ast.parse(ast.unparse(node), mode='exec')
            compiled_function_code = compile(function_ast, filename="<ast>", mode='exec')
            exec(compiled_function_code, global_dict)

        elif isinstance(node, ast.Name):
            if print_flag:
                print(indent + f"Variable Name: {node.id}")
    except:
        pass

    result_dict['node_history'].pop()


def get_bug_info(pid, generated_code):
    # load test case and global dict
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    test_case_result = code_context_2_testcase(pid, ds1000[pid])
    if test_case_result:
        global_dict = test_case_result[0]['global_dict']
        test_case = [{
            'input': test_case_result[0]['input'],
            'output': test_case_result[0]['output']
        }]
    else:
        global_dict = {}
        test_case = []

    last_exec_part = ''
    last_exec_part_value = ''
    last_unexec_part = ''
    last_exec_part_type = None
    last_unexec_part_type = None
    result_dict = {
        'node_history': [],
    }
    try:
        parsed_code = ast.parse(generated_code)

        execute_and_explain(parsed_code, global_dict, result_dict, pid, level=0)

        if 'ans_dict' in result_dict:
            last_exec_part, last_exec_part_level, last_exec_part_type = result_dict['ans_dict']['history'][-1]
            last_exec_part_value = result_dict['ans_dict']['value']
            last_unexec_part = ''
            for history_node in reversed(result_dict['ans_dict']['history']):
                if history_node[1] == last_exec_part_level - 1:
                    last_unexec_part = history_node[0]
                    last_unexec_part_type = history_node[2]
                    break
        else:
            if 'error' in global_dict:
                pass
    except Exception as e:
        pass
    if '__builtins__' in global_dict:
        global_dict.pop('__builtins__')
    res = {
        'last_exec_part': last_exec_part,
        'last_exec_part_value': last_exec_part_value,
        'last_exec_part_type': last_exec_part_type,
        'last_unexec_part': last_unexec_part,
        'last_unexec_part_type': last_unexec_part_type,
        'global_dict': global_dict,
        'result_dict': result_dict,
        'test_case': test_case
    }

    return res
