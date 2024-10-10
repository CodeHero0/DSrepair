import gzip
import json
import os
import re
import pickle
import types
from pprint import pprint

import yaml
import pandas as pd
import copy
import math
import io
import scipy
from scipy.integrate import simpson
from scipy.special import comb
from scipy.stats import rankdata
from scipy import interpolate as intp
from scipy import optimize
from scipy import stats
from scipy import sparse
from scipy import signal
import scipy.fft as sf
from scipy import integrate, stats
from scipy.spatial import distance
from scipy.optimize import minimize
import scipy.stats as ss
from scipy.sparse import csr_matrix
from scipy import interpolate
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import minmax_scale
from sklearn.datasets import make_classification, load_iris
from sklearn.datasets import fetch_california_housing
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.calibration import CalibratedClassifierCV
import sklearn.svm as suppmach
from itertools import product
import torch
import itertools
import itertools as IT
import numpy as np
import tensorflow as tf
import random
from scipy.optimize import curve_fit
from code_test import run_test_conversation

def test_code_standalone():
    file_path = 'intermediate_result/ds1000_model_gpt-3.5-turbo_fl_kg.json_4'
    with open(file_path, 'r') as f:
        response_list = json.load(f)
    test_res_file_path = run_test_conversation(response_list, file_path, False)
    count = 0
    with open(test_res_file_path, 'r') as f:
        for line in f.readlines():
            content = json.loads(line)
            if content['returncode'] == 0:
                count += 1

    print(count)


tf_list = [680, 681, 688, 689, 690, 691, 692, 693, 698, 699, 700, 702, 703, 704, 705]
def use_extracted_function(func_name, local_namespace, *args):
    library_str = ''
    for key in local_namespace:
        if isinstance(local_namespace[key], types.ModuleType):
            library_str += 'import %s ' % (key)+'\n'
    print(library_str)
    exec(library_str)
    if func_name in local_namespace:
        func = local_namespace[func_name]
        return func(*args)
    else:
        raise ValueError(f"Function {func_name} not found in the defined functions.")

def extract_test_cases(test_case_id, code_context):
    local_namespace = {}

    exec(code_context + '\ntest_input, expected_result = generate_test_case(%s)' % (test_case_id), None, local_namespace)
    test_input, expected_result = local_namespace['test_input'], local_namespace['expected_result']
    return test_input, expected_result, local_namespace

def code_context_2_testcase(pid, problem):
    spoiled_test_cases = []
    tf_list = [680, 681, 688, 689, 690, 691, 692, 693, 698, 699, 700, 702, 703, 704, 705]
    if pid in tf_list:
        code_context = problem['code_context'].replace('copy.deepcopy(test_input)', 'test_input')
    elif pid in [908, 909, 910]:
        return []
    else:
        code_context = problem['code_context']



    spoiled_test_cases = []
    variables = []

    try:
        variable_name_pattern = r'([a-zA-Z_]\w*)\s*(?:,\s*([a-zA-Z_]\w*))?\s*=\s*test_input'
        variable_name_match = re.search(variable_name_pattern, code_context)
        if variable_name_match:
            variables = [variable_name_match.group(1)]
            if variable_name_match.group(2):
                variables.append(variable_name_match.group(2))

        pattern = r'if\s+test_case_id\s*==\s*(\d+):\s*(.*?)\s*(?=elif|else|return|def|\Z)'

        # Find all matches in the context string
        matches = re.findall(pattern, code_context, re.DOTALL)
        for match in matches:
            if 'random' in match[1]:
                continue
            else:
                test_input, expected_result, local_namespace = extract_test_cases(int(match[0]), code_context)
                global_dict = {}

                # test input
                if variables == []:
                    pass
                elif isinstance(test_input, tuple):
                    for i, variable in enumerate(variables):
                        global_dict[variable] = test_input[i]
                else:
                    global_dict[variables[0]] = test_input
                # library
                for key in local_namespace:
                    if isinstance(local_namespace[key], types.ModuleType):
                        global_dict[key] = local_namespace[key]


                spoiled_test_cases.append({'input': test_input, 'output': expected_result, 'global_dict': global_dict})

    except:
        return spoiled_test_cases


    return spoiled_test_cases
