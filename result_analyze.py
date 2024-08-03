import json
import gzip
import tiktoken
from util import filter_error_problem
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.lines import Line2D
import upsetplot
import pandas as pd
import numpy as np

# you have to load the experiment result before running the code

ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]

first_test_res_list = []
target_file = 'ds1000_t_0.json'
with open('intermediate_result/first_test/enriched_' + target_file, 'r') as f:
    for line in f.readlines():
        first_test_res_list.append(json.loads(line))
error_res_list = filter_error_problem(first_test_res_list, ds1000)


def count_token(text, model='gpt-3.5-turbo'):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    num_tokens = len(tokens)
    return num_tokens


def count_mean_token(res_list):
    request_token_num_list = []
    response_token_num_list = []
    for i, res in enumerate(res_list):
        # print(i)
        request_token_num = 0
        response_token_num = 0
        for message in res['message']:
            request_token_num += count_token(message['content'])
        if 'choices' in res['completion']:
            response_token_num += count_token(res['completion']['choices'][0]['message']['content'])
        elif 'error' in res['completion']:
            response_token_num += count_token(res['completion']['error']['message'])
        # else:

        # print(request_token_num, response_token_num)
        request_token_num_list.append(request_token_num)
        response_token_num_list.append(response_token_num)

    return sum(request_token_num_list) / len(request_token_num_list), sum(response_token_num_list) / len(
        response_token_num_list)


def count_fixed_number(res_list):
    count = 0
    for res in res_list:
        if res['returncode'] == 0:
            count += 1
    return count


def load_res_list(file_name):
    tmp_list = []
    with open(file_name, 'r') as f:
        for line in f.readlines():
            content = json.loads(line)
            tmp_list.append(content)
    return tmp_list


def count_pass_rate_per_library(ds1000, item, latex=False):
    unsolved_pid_list = []
    for res in item[1]:
        if res['returncode'] != 0:
            unsolved_pid_list.append(res['pid'])

    numpy_solved = []
    pandas_solved = []
    scipy_solved = []
    sklearn_solved = []
    matplotlib_solved = []
    pytorch_solved = []
    tensorflow_solved = []

    numpy_total = 0
    pandas_total = 0
    scipy_total = 0
    sklearn_total = 0
    matplotlib_total = 0
    pytorch_total = 0
    tensorflow_total = 0

    for pid, problem in enumerate(ds1000):
        if problem['metadata']['library'].lower() == 'numpy':
            numpy_total += 1
        elif problem['metadata']['library'].lower() == 'pandas':
            pandas_total += 1
        elif problem['metadata']['library'].lower() == 'scipy':
            scipy_total += 1
        elif problem['metadata']['library'].lower() == 'sklearn':
            sklearn_total += 1
        elif problem['metadata']['library'].lower() == 'matplotlib':
            matplotlib_total += 1
        elif problem['metadata']['library'].lower() == 'pytorch':
            pytorch_total += 1
        elif problem['metadata']['library'].lower() == 'tensorflow':
            tensorflow_total += 1

        if pid not in unsolved_pid_list:
            if problem['metadata']['library'].lower() == 'numpy':
                numpy_solved.append(pid)
            elif problem['metadata']['library'].lower() == 'pandas':
                pandas_solved.append(pid)
            elif problem['metadata']['library'].lower() == 'scipy':
                scipy_solved.append(pid)
            elif problem['metadata']['library'].lower() == 'sklearn':
                sklearn_solved.append(pid)
            elif problem['metadata']['library'].lower() == 'matplotlib':
                matplotlib_solved.append(pid)
            elif problem['metadata']['library'].lower() == 'pytorch':
                pytorch_solved.append(pid)
            elif problem['metadata']['library'].lower() == 'tensorflow':
                tensorflow_solved.append(pid)

    if latex:
        # print('numpy & pandas & scipy & sklearn & matplotlib & pytorch & tensorflow & total')
        print('%s & %s & %s & %s & %s & %s & %s & %s & %s \\\\' % (item[0],
                                                                   "{:.2f}\%".format(
                                                                       len(numpy_solved) / numpy_total * 100),
                                                                   "{:.2f}\%".format(
                                                                       len(pandas_solved) / pandas_total * 100),
                                                                   "{:.2f}\%".format(
                                                                       len(scipy_solved) / scipy_total * 100),
                                                                   "{:.2f}\%".format(
                                                                       len(sklearn_solved) / sklearn_total * 100),
                                                                   "{:.2f}\%".format(
                                                                       len(matplotlib_solved) / matplotlib_total * 100),
                                                                   "{:.2f}\%".format(
                                                                       len(pytorch_solved) / pytorch_total * 100),
                                                                   "{:.2f}\%".format(
                                                                       len(tensorflow_solved) / tensorflow_total * 100),
                                                                   "{:.2f}\%".format(
                                                                       (1000 - len(unsolved_pid_list)) / 1000 * 100)))
    else:
        # print('numpy\tpandas\tscipy\tsklearn\tmatplotlib\tpytorch\ttensorflow\ttotal')
        print('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' % (item[0],
                                                      "{:.2f}%".format(len(numpy_solved) / numpy_total * 100),
                                                      "{:.2f}%".format(len(pandas_solved) / pandas_total * 100),
                                                      "{:.2f}%".format(len(scipy_solved) / scipy_total * 100),
                                                      "{:.2f}%".format(len(sklearn_solved) / sklearn_total * 100),
                                                      "{:.2f}%".format(len(matplotlib_solved) / matplotlib_total * 100),
                                                      "{:.2f}%".format(len(pytorch_solved) / pytorch_total * 100),
                                                      "{:.2f}%".format(len(tensorflow_solved) / tensorflow_total * 100),
                                                      "{:.2f}%".format((1000 - len(unsolved_pid_list)) / 1000 * 100)))


def count_fix_number_fix_rate(ds1000, item, error_res_list, latex=False):
    total_error_number = len(error_res_list)
    numpy_solved = []
    pandas_solved = []
    scipy_solved = []
    sklearn_solved = []
    matplotlib_solved = []
    pytorch_solved = []
    tensorflow_solved = []

    numpy_total = 0
    pandas_total = 0
    scipy_total = 0
    sklearn_total = 0
    matplotlib_total = 0
    pytorch_total = 0
    tensorflow_total = 0

    for content in item[1]:
        if ds1000[content['pid']]['metadata']['library'].lower() == 'numpy':
            numpy_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'pandas':
            pandas_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'scipy':
            scipy_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'sklearn':
            sklearn_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'matplotlib':
            matplotlib_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'pytorch':
            pytorch_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'tensorflow':
            tensorflow_total += 1

        if content['returncode'] == 0:
            if ds1000[content['pid']]['metadata']['library'].lower() == 'numpy':
                numpy_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'pandas':
                pandas_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'scipy':
                scipy_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'sklearn':
                sklearn_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'matplotlib':
                matplotlib_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'pytorch':
                pytorch_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'tensorflow':
                tensorflow_solved.append(content['pid'])

    if latex:
        print('%s & %s & %s \\\\' % (item[0], count_fixed_number(item[1]),
                                     "{:.2f}\%".format(count_fixed_number(item[1]) / total_error_number * 100)))

    else:
        print('%s\t%s\t%s' % (
        item[0], count_fixed_number(item[1]), "{:.2f}%".format(count_fixed_number(item[1]) / total_error_number * 100)))


def count_fix_rate_token_usage(ds1000, item, error_res_list, latex=False):
    total_error_number = len(error_res_list)
    numpy_solved = []
    pandas_solved = []
    scipy_solved = []
    sklearn_solved = []
    matplotlib_solved = []
    pytorch_solved = []
    tensorflow_solved = []

    numpy_total = 0
    pandas_total = 0
    scipy_total = 0
    sklearn_total = 0
    matplotlib_total = 0
    pytorch_total = 0
    tensorflow_total = 0

    for content in item[1]:
        if ds1000[content['pid']]['metadata']['library'].lower() == 'numpy':
            numpy_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'pandas':
            pandas_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'scipy':
            scipy_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'sklearn':
            sklearn_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'matplotlib':
            matplotlib_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'pytorch':
            pytorch_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'tensorflow':
            tensorflow_total += 1

        if content['returncode'] == 0:
            if ds1000[content['pid']]['metadata']['library'].lower() == 'numpy':
                numpy_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'pandas':
                pandas_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'scipy':
                scipy_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'sklearn':
                sklearn_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'matplotlib':
                matplotlib_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'pytorch':
                pytorch_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'tensorflow':
                tensorflow_solved.append(content['pid'])

    if latex:
        if len(item) == 2:
            input_token, output_token = count_mean_token(item[1])

            print('%s & %s & %s & %s & %s \\\\' % (item[0],
                                                   round(input_token, 2),
                                                   round(output_token, 2),
                                                   round(sum([input_token, output_token]), 2),
                                                   "{:.2f}\%".format(
                                                       count_fixed_number(item[1]) / total_error_number * 100)))
        else:
            input_token, output_token = count_mean_token(item[1])
            input_token_additional, output_token_additional = count_mean_token(item[2])
            print('%s & %s & %s & %s & %s  \\\\' % (item[0],
                                                    round(sum([input_token, input_token_additional,
                                                               output_token_additional]), 2),
                                                    round(output_token, 2),
                                                    round(sum([input_token, output_token, input_token_additional,
                                                               output_token_additional]), 2),
                                                    "{:.2f}\%".format(
                                                        count_fixed_number(item[1]) / total_error_number * 100)))

    else:
        if len(item) == 2:
            input_token, output_token = count_mean_token(item[1])
            print('%s\t%s\t%s\t%s\t%s' % (item[0],
                                          round(input_token, 2),
                                          round(output_token, 2),
                                          round(sum([input_token, output_token]), 2),
                                          "{:.2f}\%".format(count_fixed_number(item[1]) / total_error_number * 100)))
        else:
            input_token, output_token = count_mean_token(item[1])
            input_token_additional, output_token_additional = count_mean_token(item[2])
            print('%s\t%s\t%s\t%s\t%s' % (item[0],
                                          round(sum([input_token, input_token_additional, output_token_additional]), 2),
                                          round(output_token, 2),
                                          round(sum([input_token, output_token, input_token_additional,
                                                     output_token_additional]), 2),
                                          "{:.2f}\%".format(count_fixed_number(item[1]) / total_error_number * 100)))


def calculate_money_cost(item, model):
    if model == 0:
        model = 'GPT-3.5-turbo'
    elif model == 1:
        model = 'DeepSeek-Coder-V2'
    elif model == 2:
        model = 'Codestral-2405'

    price = {
        # $0.5 /1M tokens	$1.5 /1M tokens
        'GPT-3.5-turbo': {
            'input': 0.5,
            'output': 1.5
        },
        # $0.14 /1M tokens	$0.28 /1M tokens
        'DeepSeek-Coder-V2': {
            'input': 0.14,
            'output': 0.28
        },
        # $1 /1M tokens	$3 /1M tokens
        'Codestral-2405': {
            'input': 1,
            'output': 3
        },
    }

    cost = 0

    if len(item) == 2:
        input_token, output_token = count_mean_token(item[1])
        cost += input_token * price[model]['input']
        cost += output_token * price[model]['output']
    else:
        input_token_1, output_token_1 = count_mean_token(item[1])
        input_token_2, output_token_2 = count_mean_token(item[2])
        cost += (input_token_1 + input_token_2) * price[model]['input']
        cost += (output_token_1 + output_token_2) * price[model]['output']

    return cost / 1000000


def count_fix_rate_token_usage_overall(overall_list, latex=True):
    for i in range(len(overall_list[0])):
        if latex:
            if len(overall_list[0][i]) == 2:
                print('%s & %s & %s & %s & %s & %s & %s & %s & %s & %s \\\\' %
                      (overall_list[0][i][0],
                       "{:.2f}\%".format(
                           (count_fixed_number(overall_list[0][i][1]) / len(overall_list[0][i][1]) * 100)),
                       round(sum(count_mean_token(overall_list[0][i][1])), 2),
                       '\$%s' % (round(calculate_money_cost(overall_list[0][i], 0), 5)),
                       "{:.2f}\%".format(
                           (count_fixed_number(overall_list[1][i][1]) / len(overall_list[1][i][1]) * 100)),
                       round(sum(count_mean_token(overall_list[1][i][1])), 2),
                       '\$%s' % (round(calculate_money_cost(overall_list[1][i], 1), 5)),
                       "{:.2f}\%".format(
                           (count_fixed_number(overall_list[2][i][1]) / len(overall_list[2][i][1]) * 100)),
                       round(sum(count_mean_token(overall_list[2][i][1])), 2),
                       '\$%s' % (round(calculate_money_cost(overall_list[2][i], 2), 5)),
                       ))
            else:
                print('%s & %s & %s & %s & %s & %s & %s & %s & %s & %s \\\\' %
                      (overall_list[0][i][0],
                       "{:.2f}\%".format(
                           (count_fixed_number(overall_list[0][i][1]) / len(overall_list[0][i][1]) * 100)),
                       round(sum([sum(count_mean_token(overall_list[0][i][1])),
                                  sum(count_mean_token(overall_list[0][i][2]))]), 2),
                       '\$%s' % (round(calculate_money_cost(overall_list[0][i], 0), 5)),
                       "{:.2f}\%".format(
                           (count_fixed_number(overall_list[1][i][1]) / len(overall_list[1][i][1]) * 100)),
                       round(sum([sum(count_mean_token(overall_list[1][i][1])),
                                  sum(count_mean_token(overall_list[1][i][2]))]), 2),
                       '\$%s' % (round(calculate_money_cost(overall_list[1][i], 1), 5)),
                       "{:.2f}\%".format(
                           (count_fixed_number(overall_list[2][i][1]) / len(overall_list[2][i][1]) * 100)),
                       round(sum([sum(count_mean_token(overall_list[2][i][1])),
                                  sum(count_mean_token(overall_list[2][i][2]))]), 2),
                       '\$%s' % (round(calculate_money_cost(overall_list[2][i], 2), 5)),
                       ))


def count_fix_rate_per_library(ds1000, item, latex=False, total=False):
    # total_error_number = len(error_res_list)
    numpy_solved = []
    pandas_solved = []
    scipy_solved = []
    sklearn_solved = []
    matplotlib_solved = []
    pytorch_solved = []
    tensorflow_solved = []
    solved = []

    numpy_total = 0
    pandas_total = 0
    scipy_total = 0
    sklearn_total = 0
    matplotlib_total = 0
    pytorch_total = 0
    tensorflow_total = 0
    total_number = 0

    for content in item[1]:
        total_number += 1
        if ds1000[content['pid']]['metadata']['library'].lower() == 'numpy':
            numpy_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'pandas':
            pandas_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'scipy':
            scipy_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'sklearn':
            sklearn_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'matplotlib':
            matplotlib_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'pytorch':
            pytorch_total += 1
        elif ds1000[content['pid']]['metadata']['library'].lower() == 'tensorflow':
            tensorflow_total += 1

        if content['returncode'] == 0:
            solved.append(content['pid'])
            if ds1000[content['pid']]['metadata']['library'].lower() == 'numpy':
                numpy_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'pandas':
                pandas_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'scipy':
                scipy_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'sklearn':
                sklearn_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'matplotlib':
                matplotlib_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'pytorch':
                pytorch_solved.append(content['pid'])
            elif ds1000[content['pid']]['metadata']['library'].lower() == 'tensorflow':
                tensorflow_solved.append(content['pid'])

    if latex:
        # print('numpy & pandas & scipy & sklearn & matplotlib & pytorch & tensorflow')
        if total:
            print(
                '& %s & %s (%s) & %s (%s) & %s (%s) & %s (%s) & %s (%s) & %s (%s) & %s (%s) & %s (%s) \\\\' % (item[0],
                                                                                                               len(numpy_solved),
                                                                                                               "{:.2f}\%".format(
                                                                                                                   len(numpy_solved) / numpy_total * 100),
                                                                                                               len(pandas_solved),
                                                                                                               "{:.2f}\%".format(
                                                                                                                   len(pandas_solved) / pandas_total * 100),
                                                                                                               len(scipy_solved),
                                                                                                               "{:.2f}\%".format(
                                                                                                                   len(scipy_solved) / scipy_total * 100),
                                                                                                               len(sklearn_solved),
                                                                                                               "{:.2f}\%".format(
                                                                                                                   len(sklearn_solved) / sklearn_total * 100),
                                                                                                               len(matplotlib_solved),
                                                                                                               "{:.2f}\%".format(
                                                                                                                   len(matplotlib_solved) / matplotlib_total * 100),
                                                                                                               len(pytorch_solved),
                                                                                                               "{:.2f}\%".format(
                                                                                                                   len(pytorch_solved) / pytorch_total * 100),
                                                                                                               len(tensorflow_solved),
                                                                                                               "{:.2f}\%".format(
                                                                                                                   len(tensorflow_solved) / tensorflow_total * 100),
                                                                                                               len(solved),
                                                                                                               "{:.2f}\%".format(
                                                                                                                   len(solved) / total_number * 100)))
        else:
            print('& %s & %s & %s & %s & %s & %s & %s & %s \\\\' % (item[0],
                                                                    "{:.2f}\%".format(
                                                                        len(numpy_solved) / numpy_total * 100),
                                                                    "{:.2f}\%".format(
                                                                        len(pandas_solved) / pandas_total * 100),
                                                                    "{:.2f}\%".format(
                                                                        len(scipy_solved) / scipy_total * 100),
                                                                    "{:.2f}\%".format(
                                                                        len(sklearn_solved) / sklearn_total * 100),
                                                                    "{:.2f}\%".format(
                                                                        len(matplotlib_solved) / matplotlib_total * 100),
                                                                    "{:.2f}\%".format(
                                                                        len(pytorch_solved) / pytorch_total * 100),
                                                                    "{:.2f}\%".format(
                                                                        len(tensorflow_solved) / tensorflow_total * 100)))
            # "{:.2f}\%".format(len(solved) / total_number * 100)))
    else:
        # print('numpy\tpandas\tscipy\tsklearn\tmatplotlib\tpytorch\ttensorflow')
        if total:
            print('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s (%s) ' % (item[0],
                                                                "{:.2f}%".format(len(numpy_solved) / numpy_total * 100),
                                                                "{:.2f}%".format(
                                                                    len(pandas_solved) / pandas_total * 100),
                                                                "{:.2f}%".format(len(scipy_solved) / scipy_total * 100),
                                                                "{:.2f}%".format(
                                                                    len(sklearn_solved) / sklearn_total * 100),
                                                                "{:.2f}%".format(
                                                                    len(matplotlib_solved) / matplotlib_total * 100),
                                                                "{:.2f}%".format(
                                                                    len(pytorch_solved) / pytorch_total * 100),
                                                                "{:.2f}\%".format(
                                                                    len(tensorflow_solved) / tensorflow_total * 100),
                                                                "{:.2f}\%".format(len(solved) / total_number * 100),
                                                                len(solved)))
            print('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' % (item[0],
                                                      "{:.2f}%".format(len(numpy_solved) / numpy_total * 100),
                                                      "{:.2f}%".format(len(pandas_solved) / pandas_total * 100),
                                                      "{:.2f}%".format(len(scipy_solved) / scipy_total * 100),
                                                      "{:.2f}%".format(len(sklearn_solved) / sklearn_total * 100),
                                                      "{:.2f}%".format(len(matplotlib_solved) / matplotlib_total * 100),
                                                      "{:.2f}%".format(len(pytorch_solved) / pytorch_total * 100),
                                                      "{:.2f}\%".format(
                                                          len(tensorflow_solved) / tensorflow_total * 100)))
            # "{:.2f}\%".format(len(solved) / total_number * 100)))


def overlap_rate(target_list):
    # calculate overlap between stderr, local, global
    if len(target_list) == 2:
        a = target_list[0]
        b = target_list[1]

        ab = []
        a_b = []
        _ab = []
        for i in range(len(a)):
            if a[i]['returncode'] == 0 and b[i]['returncode'] == 0:
                ab.append(a[i]['pid'])
            elif a[i]['returncode'] == 0 and b[i]['returncode'] != 0:
                a_b.append(a[i]['pid'])
            elif a[i]['returncode'] != 0 and b[i]['returncode'] == 0:
                _ab.append(b[i]['pid'])

        return ab, a_b, _ab

    elif len(target_list) == 3:
        a = target_list[0]
        b = target_list[1]
        c = target_list[2]

        abc = []
        _abc = []
        a_bc = []
        ab_c = []
        _a_bc = []
        a_b_c = []
        _ab_c = []

        for i in range(len(a)):
            if a[i]['returncode'] == 0 and b[i]['returncode'] == 0 and c[i]['returncode'] == 0:
                abc.append(a[i]['pid'])
            elif a[i]['returncode'] != 0 and b[i]['returncode'] == 0 and c[i]['returncode'] == 0:
                _abc.append(a[i]['pid'])
            elif a[i]['returncode'] == 0 and b[i]['returncode'] != 0 and c[i]['returncode'] == 0:
                a_bc.append(a[i]['pid'])
            elif a[i]['returncode'] == 0 and b[i]['returncode'] == 0 and c[i]['returncode'] != 0:
                ab_c.append(a[i]['pid'])
            elif a[i]['returncode'] == 0 and b[i]['returncode'] != 0 and c[i]['returncode'] != 0:
                a_b_c.append(a[i]['pid'])
            elif a[i]['returncode'] != 0 and b[i]['returncode'] == 0 and c[i]['returncode'] != 0:
                _ab_c.append(a[i]['pid'])
            elif a[i]['returncode'] != 0 and b[i]['returncode'] != 0 and c[i]['returncode'] == 0:
                _a_bc.append(a[i]['pid'])
        return abc, _abc, a_bc, ab_c, a_b_c, _ab_c, _a_bc

    return


def count_improve_rate(compare_list, target, latex=False):
    target_fix_number = count_fixed_number(target[1])
    print(target_fix_number)
    for item in compare_list:
        tmp_fix_number = count_fixed_number(item[1])
        if latex:
            print('%s & %s & %s' % (item[0],
                                    tmp_fix_number,
                                    "{:.2f}\%".format((target_fix_number - tmp_fix_number) / tmp_fix_number * 100)))
        else:
            print(item[0], (target_fix_number - tmp_fix_number) / tmp_fix_number)


def count_improve_rate_overall(overall_list, latex=True):
    target_fix_number_list = [count_fixed_number(x[-1][1]) for x in overall_list]
    for i in range(len(overall_list[0])):
        tmp_fix_number_list = [count_fixed_number(overall_list[x][i][1]) for x in range(3)]
        if latex:
            print('%s & %s & %s & %s & %s & %s & %s \\\\' %
                  (overall_list[0][i][0],
                   tmp_fix_number_list[0],
                   "{:.2f}\%".format(
                       (target_fix_number_list[0] - tmp_fix_number_list[0]) / tmp_fix_number_list[0] * 100),
                   tmp_fix_number_list[1],
                   "{:.2f}\%".format(
                       (target_fix_number_list[1] - tmp_fix_number_list[1]) / tmp_fix_number_list[1] * 100),
                   tmp_fix_number_list[2],
                   "{:.2f}\%".format(
                       (target_fix_number_list[2] - tmp_fix_number_list[2]) / tmp_fix_number_list[2] * 100)
                   ))


def draw_scatter_plot_fix_rate_and_token_usage(input_list, save=False):
    name_list = []
    figsize = (12, 8)
    fig, ax = plt.subplots(figsize=figsize)

    point_list_gpt = []
    point_list_deepseek = []
    point_list_codestral = []

    markers = {'Code-Search': 'o',
               'Chat-Repair': 's',
               'Self-Debugging-S': '^',
               'Self-Debugging-E': 'D',
               'Self-Repair': 'P',
               'DSrepair': '*'}
    color_deepseek = '#ef476f'
    color_gpt = '#26547c'
    color_codestral = '#ffd166'
    for item in input_list[0]:
        tmp_fixed_number = count_fixed_number(item[1])
        fix_rate = tmp_fixed_number / 562
        if len(item) == 3:
            token_usage = sum(count_mean_token(item[1])) + sum(count_mean_token(item[2]))
        else:
            token_usage = sum(count_mean_token(item[1]))
        name_list.append(item[0])
        point_list_gpt.append((item[0], token_usage, fix_rate))
        # point_list_gpt_x.append(token_usage)
        # point_list_gpt_y.append(fix_rate)

    for item in input_list[1]:
        tmp_fixed_number = count_fixed_number(item[1])
        fix_rate = tmp_fixed_number / 562
        if len(item) == 3:
            token_usage = sum(count_mean_token(item[1])) + sum(count_mean_token(item[2]))
        else:
            token_usage = sum(count_mean_token(item[1]))
        name_list.append(item[0])
        point_list_deepseek.append((item[0], token_usage, fix_rate))
        # point_list_deepseek_x.append(token_usage)
        # point_list_deepseek_y.append(fix_rate)

    for item in input_list[2]:
        tmp_fixed_number = count_fixed_number(item[1])
        fix_rate = tmp_fixed_number / 562
        if len(item) == 3:
            token_usage = sum(count_mean_token(item[1])) + sum(count_mean_token(item[2]))
        else:
            token_usage = sum(count_mean_token(item[1]))
        name_list.append(item[0])
        point_list_codestral.append((item[0], token_usage, fix_rate))
        # point_list_deepseek_x.append(token_usage)
        # point_list_deepseek_y.append(fix_rate)

    # for (x, y), marker, name in zip(point_list_gpt, markers, name_list):
    #     plt.scatter(x, y, color=color_gpt, marker=marker, label=name, s=100)
    #
    # for (x, y), marker, name in zip(point_list_deepseek, markers, name_list):
    #     plt.scatter(x, y, color=color_deepseek, marker=marker, label=name, s=100)

    # sort the list
    # point_list_gpt = sorted(point_list_gpt, key=lambda x: x[1])
    # point_list_deepseek = sorted(point_list_deepseek, key=lambda x: x[1])

    scatter_handles = []
    for i in range(len(point_list_gpt)):
        item = point_list_gpt[i]
        label = item[0]
        marker = markers[label]
        scatter = ax.scatter(item[1], item[2], label=label, marker=marker, color=color_gpt, s=200)
        scatter_handles.append(scatter)
        # if i > 0 and i <len(point_list_gpt):  # Draw lines between points
        #     ax.plot([point_list_gpt[i-1][1], point_list_gpt[i][1]],
        #              [point_list_gpt[i-1][2], point_list_gpt[i][2]], 'k-', color=color_gpt)

    for i in range(len(point_list_deepseek)):
        item = point_list_deepseek[i]
        label = item[0]
        marker = markers[label]
        ax.scatter(item[1], item[2], label=label, marker=marker, color=color_deepseek, s=200)
        # if i > 0 and i <len(point_list_deepseek):  # Draw lines between points
        #     ax.plot([point_list_deepseek[i-1][1], point_list_deepseek[i][1]],
        #              [point_list_deepseek[i-1][2], point_list_deepseek[i][2]], 'k-', color=color_deepseek)

    for i in range(len(point_list_codestral)):
        item = point_list_codestral[i]
        label = item[0]
        marker = markers[label]
        ax.scatter(item[1], item[2], label=label, marker=marker, color=color_codestral, s=200)

    # plt.plot([x[1] for x in point_list_gpt], [x[2] for x in point_list_gpt], color='r', marker='o', label='Line Data 1')
    # plt.plot([x[1] for x in point_list_deepseek], [x[2] for x in point_list_deepseek], color='m', marker='s', label='Line Data 2')

    line_handles = [Line2D([0], [0], color=color_gpt, label='GPT-3.5-turbo'),
                    Line2D([0], [0], color=color_deepseek, label='DeepSeek-Coder'),
                    Line2D([0], [0], color=color_codestral, label='Codestral')]

    ax.set_title('Scatter Plot of Token usage and Fix Rate', fontsize=18)
    ax.set_xlabel('Token Usage', fontsize=18)
    ax.set_ylabel('Fix Rate', fontsize=18)

    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    # ax.legend(['GPT-3.5-turbo', 'Deepseek-coder'], fontsize=16, loc='center left', bbox_to_anchor=(1, 0.5))
    # ax.legend(fontsize=16, loc='center left', bbox_to_anchor=(1, 0.5))

    scatter_legend = ax.legend(handles=scatter_handles, loc='upper left', title='Prompt Engineering Strategy',
                               bbox_to_anchor=(1, 0.82), markerscale=0.7)

    ax.add_artist(scatter_legend)

    # Create the second legend for the line
    line_legend = ax.legend(handles=line_handles, loc='upper left', title='Model', markerscale=2,
                            bbox_to_anchor=(1, 1))
    ax.add_artist(line_legend)

    ax.tick_params(axis='x', labelsize=18)
    ax.tick_params(axis='y', labelsize=18)

    plt.subplots_adjust(right=0.65)
    if save:
        plt.savefig('fig/scatter_plot_token_usage_and_fix_rate.pdf')
    else:
        plt.show()


def from_memberships(memberships, data=None):
    from numbers import Number
    def _convert_to_pandas(data, copy=True):
        is_series = False
        if hasattr(data, "loc"):
            if copy:
                data = data.copy(deep=False)
            is_series = data.ndim == 1
        elif len(data):
            try:
                is_series = isinstance(data[0], Number)
            except KeyError:
                is_series = False
        return pd.Series(data) if is_series else pd.DataFrame(data)

    df = pd.DataFrame([{name: True for name in names} for names in memberships])
    for set_name in df.columns:
        if not hasattr(set_name, "lower"):
            raise ValueError("Category names should be strings")
    if df.shape[1] == 0:
        raise ValueError("Require at least one category. None were found.")
    # df.sort_index(axis=1, inplace=True)
    df.fillna(False, inplace=True)
    df = df.astype(bool)
    df.set_index(list(df.columns), inplace=True)
    if data is None:
        return df.assign(ones=1)["ones"]

    data = _convert_to_pandas(data)
    if len(data) != len(df):
        raise ValueError(
            "memberships and data must have the same length. "
            "Got len(memberships) == %d, len(data) == %d"
            % (len(memberships), len(data))
        )
    data.index = df.index
    return data


def draw_upsetplot(item_list, suffix, save=False):
    passed_case_dic = {}

    for item in item_list:
        passed_case_list = []
        for content in item[1]:
            if content['returncode'] == 0:
                passed_case_list.append(content['pid'])
        passed_case_dic[item[0]] = passed_case_list

    overlap_dic = {}

    for key in passed_case_dic:
        tmp_overlap_list = []
        if key != 'DSrepair':
            for pid in passed_case_dic[key]:
                if pid in passed_case_dic['DSrepair']:
                    tmp_overlap_list.append(pid)

            overlap_dic[key + '_DSrepair'] = tmp_overlap_list

    overlap_dic['all_overlap'] = list(set(passed_case_dic['DSrepair']).intersection(set(passed_case_dic['Code-Search']),
                                                                                    set(passed_case_dic['Chat-Repair']),
                                                                                    set(passed_case_dic[
                                                                                            'Self-Debugging-S']),
                                                                                    set(passed_case_dic[
                                                                                            'Self-Debugging-E']),
                                                                                    set(passed_case_dic[
                                                                                            'Self-Repair'])))

    values = []

    for key in overlap_dic:
        print(key)
        values.append(len(overlap_dic[key]))
    memberships = [
        ['DSrepair', 'Code-Search'],
        ['DSrepair', 'Chat-Repair'],
        ['DSrepair', 'Self-Debugging-S'],
        ['DSrepair', 'Self-Debugging-E'],
        ['DSrepair', 'Self-Repair'],
        ['DSrepair', 'Code-Search', 'Chat-Repair', 'Self-Debugging-S', 'Self-Debugging-E', 'Self-Repair'],
    ]
    a = from_memberships(memberships, data=values)
    plt.figure(figsize=(8, 10))
    upsetplot.plot(a, show_counts="{:,}", totals_plot_elements=0, sort_categories_by='input',
                   facecolor='#233d4d')
    if save:
        plt.savefig('fig/RQ1_upsetplot_%s.pdf' % (suffix))
    else:
        plt.show()


def load_data_overall():
    gpt_list = [
        ['Code-Search', a_code_search],
        ['Chat-Repair', a_stderr],
        ['Self-Debugging-S', a_simple_feedback],
        ['Self-Debugging-E', a_line_explanation, a_additional_line_explanation_file_name],
        ['Self-Repair', a_explanation, a_additional_explanation_file_name],
        ['DSrepair', a_local_global],
    ]

    deepseek_list = [
        ['Code-Search', d_code_search],
        ['Chat-Repair', d_stderr],
        ['Self-Debugging-S', d_simple_feedback],
        ['Self-Debugging-E', d_line_explanation, d_additional_line_explanation_file_name],
        ['Self-Repair', d_explanation, d_additional_explanation_file_name],
        ['DSrepair', d_local_global],
    ]

    codestral_list = [
        ['Code-Search', c_code_search],
        ['Chat-Repair', c_stderr],
        ['Self-Debugging-S', c_simple_feedback],
        ['Self-Debugging-E', c_line_explanation, c_additional_line_explanation_file_name],
        ['Self-Repair', c_explanation, c_additional_explanation_file_name],
        ['DSrepair', c_local_global],
    ]

    input_list = [gpt_list, deepseek_list, codestral_list]

    return input_list


def load_data_ablation_study_overall():
    gpt_list = [
        ['DSrepair-API-Bug', a_plain],
        ['DSrepair-Bug', a_global],
        ['DSrepair-API', a_local],
        ['DSrepair', a_local_global],
    ]

    deepseek_list = [
        ['DSrepair-API-Bug', d_plain],
        ['DSrepair-Bug', d_global],
        ['DSrepair-API', d_local],
        ['DSrepair', d_local_global],
    ]

    codestral_list = [
        ['DSrepair-API-Bug', c_plain],
        ['DSrepair-Bug', c_global],
        ['DSrepair-API', c_local],
        ['DSrepair', c_local_global],
    ]

    input_list = [gpt_list, deepseek_list, codestral_list]

    return input_list


def RQ1_improvement_rate_overall():
    input_list = load_data_overall()
    count_improve_rate_overall(input_list)


def RQ1_fix_rate_per_library_overall():
    input_list = load_data_overall()

    print('--------------------------fix rate per library-----------------------------')
    for i in range(len(input_list)):
        if i == 0:
            print('-----GPT-3.5-turbo-----')
        elif i == 1:
            print('-----DeepSeek-Coder-----')
        elif i == 2:
            print('-----Codestral-----')
        for item in input_list[i]:
            count_fix_rate_per_library(ds1000, item, True, True)


def RQ2_token_usage_overall():
    input_list = load_data_overall()
    count_fix_rate_token_usage_overall(input_list)


def RQ3_ablation_study_overall():
    input_list = load_data_ablation_study_overall()
    print('--------------------------fix rate per library-----------------------------')
    for i in range(len(input_list)):
        if i == 0:
            print('-----GPT-3.5-turbo-----')
        elif i == 1:
            print('-----DeepSeek-Coder-----')
        elif i == 2:
            print('-----Codestral-----')
        for item in input_list[i]:
            count_fix_rate_per_library(ds1000, item, True, True)


def RQ1_draw_upsetplot_overall(save=False):
    input_list = load_data_overall()
    for i in range(len(input_list)):
        if i == 0:
            suffix = 'gpt'
        elif i == 1:
            suffix = 'deepseek'
        elif i == 2:
            suffix = 'codestral'
        draw_upsetplot(input_list[i], suffix, save)


def RQ2_draw_scatter_plot_overall(save=False):
    input_list = load_data_overall()
    draw_scatter_plot_fix_rate_and_token_usage(input_list, save)


def RQ3_draw_venn_plot_overall(save=False):
    input_list = load_data_ablation_study_overall()
    for i in range(len(input_list)):
        set_list = []
        name_list = []
        for x in input_list[i]:
            name_list.append(x[0])
            tmp_list = []
            for content in x[1]:
                if content['returncode'] == 0:
                    tmp_list.append(content['pid'])
            set_list.append(tmp_list)

        labels = venn.get_labels(set_list, fill=['number'])
        fig, ax = venn.venn4(labels, names=name_list, fontsize=24)
        if i == 0:
            suffix = 'gpt'
        elif i == 1:
            suffix = 'deepseek'
        elif i == 2:
            suffix = 'codestral'
        if save:
            fig.savefig('fig/RQ3_venn_plot_%s.pdf' % (suffix))
        else:
            fig.show()
        plt.close(fig)


def load_non_determinism_dataset_overall():
    gpt_list = [
        ['Code-Search', a_code_search],
        ['Chat-Repair', a_stderr],
        ['Self-Debugging-S', a_simple_feedback],
        ['Self-Debugging-E', a_line_explanation, a_additional_line_explanation_file_name],
        ['Self-Repair', a_explanation, a_additional_explanation_file_name],
        ['DSrepair', a_local_global],
    ]

    deepseek_list = [
        ['Code-Search', d_code_search],
        ['Chat-Repair', d_stderr],
        ['Self-Debugging-S', d_simple_feedback],
        ['Self-Debugging-E', d_line_explanation, d_additional_line_explanation_file_name],
        ['Self-Repair', d_explanation, d_additional_explanation_file_name],
        ['DSrepair', d_local_global],
    ]

    codestral_list = [
        ['Code-Search', c_code_search],
        ['Chat-Repair', c_stderr],
        ['Self-Debugging-S', c_simple_feedback],
        ['Self-Debugging-E', c_line_explanation, c_additional_line_explanation_file_name],
        ['Self-Repair', c_explanation, c_additional_explanation_file_name],
        ['DSrepair', c_local_global],
    ]

    input_list = [gpt_list, deepseek_list, codestral_list]

    return input_list


def RQ_randomness():
    # gpt
    # code search
    code_search_gpt_0_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/all_0/repair_test/ds1000_model_gpt-3.5-turbo_code_search.json_0'
    code_search_gpt_0 = load_res_list(code_search_gpt_0_name)

    code_search_gpt_1_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/all_1/repair_test/ds1000_model_gpt-3.5-turbo_code_search.json_0'
    code_search_gpt_1 = load_res_list(code_search_gpt_1_name)

    code_search_gpt_2_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/all_2/repair_test/ds1000_model_gpt-3.5-turbo_code_search.json_0'
    code_search_gpt_2 = load_res_list(code_search_gpt_2_name)

    # chat-repair
    stderr_gpt_0_name = 'intermediate_result_conversation/stderr+conversation/all_0/repair_test/ds1000_model_gpt-3.5-turbo_stderr_conversation.json_0'
    stderr_gpt_0 = load_res_list(stderr_gpt_0_name)

    stderr_gpt_1_name = 'intermediate_result_conversation/stderr+conversation/all_1/repair_test/ds1000_model_gpt-3.5-turbo_stderr_conversation.json_0'
    stderr_gpt_1 = load_res_list(stderr_gpt_1_name)

    stderr_gpt_2_name = 'intermediate_result_conversation/stderr+conversation/all_2/repair_test/ds1000_model_gpt-3.5-turbo_stderr_conversation.json_0'
    stderr_gpt_2 = load_res_list(stderr_gpt_2_name)

    # simple
    simple_gpt_0_name = 'intermediate_result_conversation/simple_feedback+conversation/all_0/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    simple_gpt_0 = load_res_list(simple_gpt_0_name)

    simple_gpt_1_name = 'intermediate_result_conversation/simple_feedback+conversation/all_1/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    simple_gpt_1 = load_res_list(simple_gpt_1_name)

    simple_gpt_2_name = 'intermediate_result_conversation/simple_feedback+conversation/all_2/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    simple_gpt_2 = load_res_list(simple_gpt_2_name)

    # explanation

    explanation_gpt_0_name = 'intermediate_result_conversation/explanation+conversation/all_0/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    explanation_gpt_0 = load_res_list(explanation_gpt_0_name)

    explanation_gpt_1_name = 'intermediate_result_conversation/explanation+conversation/all_1/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    explanation_gpt_1 = load_res_list(explanation_gpt_1_name)

    explanation_gpt_2_name = 'intermediate_result_conversation/explanation+conversation/all_2/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    explanation_gpt_2 = load_res_list(explanation_gpt_2_name)

    # line_explanation
    line_explanation_gpt_0_name = 'intermediate_result_conversation/line_explanation+conversation/all_0/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    line_explanation_gpt_0 = load_res_list(line_explanation_gpt_0_name)

    line_explanation_gpt_1_name = 'intermediate_result_conversation/line_explanation+conversation/all_1/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    line_explanation_gpt_1 = load_res_list(line_explanation_gpt_1_name)

    line_explanation_gpt_2_name = 'intermediate_result_conversation/line_explanation+conversation/all_2/repair_test/ds1000_model_gpt-3.5-turbo_triplet_stderr_conversation.json_0'
    line_explanation_gpt_2 = load_res_list(line_explanation_gpt_2_name)

    # DSrepair
    DSrepair_gpt_0_name = 'intermediate_result_conversation/sota/all_7(stderr+kg+fl)/repair_test/ds1000_model_gpt-3.5-turbo_fl_kg.json_0'
    DSrepair_gpt_0 = load_res_list(DSrepair_gpt_0_name)

    DSrepair_gpt_1_name = 'intermediate_result_conversation/sota/all_7(stderr+kg+fl)/0/repair_test/ds1000_model_gpt-3.5-turbo_fl_kg.json_0'
    DSrepair_gpt_1 = load_res_list(DSrepair_gpt_1_name)

    DSrepair_gpt_2_name = 'intermediate_result_conversation/sota/all_7(stderr+kg+fl)/repair_test/ds1000_model_gpt-3.5-turbo_fl_kg.json_0'
    DSrepair_gpt_2 = load_res_list(DSrepair_gpt_2_name)

    ##############################################################################
    # deepseek
    # code search
    code_search_deepseek_0_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/deepseek_all_0/repair_test/ds1000_model_deepseek-coder_code_search.json_0'
    code_search_deepseek_0 = load_res_list(code_search_deepseek_0_name)

    code_search_deepseek_1_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/deepseek_all_1/repair_test/ds1000_model_deepseek-coder_code_search.json_0'
    code_search_deepseek_1 = load_res_list(code_search_deepseek_1_name)

    code_search_deepseek_2_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/deepseek_all_2/repair_test/ds1000_model_deepseek-coder_code_search.json_0'
    code_search_deepseek_2 = load_res_list(code_search_deepseek_2_name)

    # chat-repair

    stderr_deepseek_0_name = 'intermediate_result_conversation/stderr+conversation/deepseek_all_0/repair_test/ds1000_model_deepseek-coder_stderr_conversation.json_0'
    stderr_deepseek_0 = load_res_list(stderr_deepseek_0_name)

    stderr_deepseek_1_name = 'intermediate_result_conversation/stderr+conversation/deepseek_all_1/repair_test/ds1000_model_deepseek-coder_stderr_conversation.json_0'
    stderr_deepseek_1 = load_res_list(stderr_deepseek_1_name)

    stderr_deepseek_2_name = 'intermediate_result_conversation/stderr+conversation/deepseek_all_2/repair_test/ds1000_model_deepseek-coder_stderr_conversation.json_0'
    stderr_deepseek_2 = load_res_list(stderr_deepseek_2_name)

    # simple
    simple_deepseek_0_name = 'intermediate_result_conversation/simple_feedback+conversation/deepseek_all_0/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    simple_deepseek_0 = load_res_list(simple_deepseek_0_name)

    simple_deepseek_1_name = 'intermediate_result_conversation/simple_feedback+conversation/deepseek_all_1/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    simple_deepseek_1 = load_res_list(simple_deepseek_1_name)

    simple_deepseek_2_name = 'intermediate_result_conversation/simple_feedback+conversation/deepseek_all_2/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    simple_deepseek_2 = load_res_list(simple_deepseek_2_name)

    # explanation
    explanation_deepseek_0_name = 'intermediate_result_conversation/explanation+conversation/deepseek_all_0/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    explanation_deepseek_0 = load_res_list(explanation_deepseek_0_name)

    explanation_deepseek_1_name = 'intermediate_result_conversation/explanation+conversation/deepseek_all_1/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    explanation_deepseek_1 = load_res_list(explanation_deepseek_1_name)

    explanation_deepseek_2_name = 'intermediate_result_conversation/explanation+conversation/deepseek_all_2/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    explanation_deepseek_2 = load_res_list(explanation_deepseek_2_name)

    # line_explanation
    line_explanation_deepseek_0_name = 'intermediate_result_conversation/line_explanation+conversation/deepseek_all_0/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    line_explanation_deepseek_0 = load_res_list(line_explanation_deepseek_0_name)

    line_explanation_deepseek_1_name = 'intermediate_result_conversation/line_explanation+conversation/deepseek_all_1/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    line_explanation_deepseek_1 = load_res_list(line_explanation_deepseek_1_name)

    line_explanation_deepseek_2_name = 'intermediate_result_conversation/line_explanation+conversation/deepseek_all_2/repair_test/ds1000_model_deepseek-coder_triplet_stderr_conversation.json_0'
    line_explanation_deepseek_2 = load_res_list(line_explanation_deepseek_2_name)

    # DSrepair
    # with open('intermediate_result_conversation/sota/deepseek_all_0(stderr+kg+fl)/repair_test/ds1000_model_deepseek-coder_fl_kg.json_0')
    DSrepair_deepseek_0_name = 'intermediate_result_conversation/sota/deepseek_all_0(stderr+kg+fl)/repair_test/ds1000_model_deepseek-coder_fl_kg.json_0'
    DSrepair_deepseek_0 = load_res_list(DSrepair_deepseek_0_name)

    DSrepair_deepseek_1_name = 'intermediate_result_conversation/sota/deepseek_all_0(stderr+kg+fl)/4/repair_test/ds1000_model_deepseek-coder_fl_kg.json_0'
    DSrepair_deepseek_1 = load_res_list(DSrepair_deepseek_1_name)

    DSrepair_deepseek_2_name = 'intermediate_result_conversation/sota/deepseek_all_0(stderr+kg+fl)/5/repair_test/ds1000_model_deepseek-coder_fl_kg.json_0'
    DSrepair_deepseek_2 = load_res_list(DSrepair_deepseek_2_name)

    ##############################################################################
    # codestral
    # code search

    code_search_codestral_0_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/codestral_all_0/repair_test/ds1000_model_codestral-latest_code_search.json_0'
    code_search_codestral_0 = load_res_list(code_search_codestral_0_name)

    code_search_codestral_1_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/codestral_all_1/repair_test/ds1000_model_codestral-latest_code_search.json_0'
    code_search_codestral_1 = load_res_list(code_search_codestral_1_name)

    code_search_codestral_2_name = 'intermediate_result_conversation/stderr+code_search(all)+conversation/codestral_all_2/repair_test/ds1000_model_codestral-latest_code_search.json_0'
    code_search_codestral_2 = load_res_list(code_search_codestral_2_name)

    # chat-repair

    stderr_codestral_0_name = 'intermediate_result_conversation/stderr+conversation/codestral_all_0/repair_test/ds1000_model_codestral-latest_stderr_conversation.json_0'
    stderr_codestral_0 = load_res_list(stderr_codestral_0_name)

    stderr_codestral_1_name = 'intermediate_result_conversation/stderr+conversation/codestral_all_1/repair_test/ds1000_model_codestral-latest_stderr_conversation.json_0'
    stderr_codestral_1 = load_res_list(stderr_codestral_1_name)

    stderr_codestral_2_name = 'intermediate_result_conversation/stderr+conversation/codestral_all_1/repair_test/ds1000_model_codestral-latest_stderr_conversation.json_0'
    stderr_codestral_2 = load_res_list(stderr_codestral_2_name)

    # simple
    simple_codestral_0_name = 'intermediate_result_conversation/simple_feedback+conversation/codestral_all_0/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    simple_codestral_0 = load_res_list(simple_codestral_0_name)

    simple_codestral_1_name = 'intermediate_result_conversation/simple_feedback+conversation/codestral_all_1/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    simple_codestral_1 = load_res_list(simple_codestral_1_name)

    simple_codestral_2_name = 'intermediate_result_conversation/simple_feedback+conversation/codestral_all_2/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    simple_codestral_2 = load_res_list(simple_codestral_2_name)

    # explanation
    explanation_codestral_0_name = 'intermediate_result_conversation/explanation+conversation/codestral_all_0/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    explanation_codestral_0 = load_res_list(explanation_codestral_0_name)

    explanation_codestral_1_name = 'intermediate_result_conversation/explanation+conversation/codestral_all_1/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    explanation_codestral_1 = load_res_list(explanation_codestral_1_name)

    explanation_codestral_2_name = 'intermediate_result_conversation/explanation+conversation/codestral_all_2/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    explanation_codestral_2 = load_res_list(explanation_codestral_2_name)

    # line_explanation

    line_explanation_codestral_0_name = 'intermediate_result_conversation/line_explanation+conversation/codestral_all_0/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    line_explanation_codestral_0 = load_res_list(line_explanation_codestral_0_name)

    line_explanation_codestral_1_name = 'intermediate_result_conversation/line_explanation+conversation/codestral_all_1/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    line_explanation_codestral_1 = load_res_list(line_explanation_codestral_1_name)

    line_explanation_codestral_2_name = 'intermediate_result_conversation/line_explanation+conversation/codestral_all_2/repair_test/ds1000_model_codestral-latest_triplet_stderr_conversation.json_0'
    line_explanation_codestral_2 = load_res_list(line_explanation_codestral_2_name)

    # DSrepair
    # with open('intermediate_result_conversation/sota/deepseek_all_0(stderr+kg+fl)/repair_test/ds1000_model_deepseek-coder_fl_kg.json_0')
    DSrepair_codestral_0_name = 'intermediate_result_conversation/sota/codestral_all_0(stderr+kg+fl)/repair_test/ds1000_model_codestral-latest_fl_kg.json_0'
    DSrepair_codestral_0 = load_res_list(DSrepair_codestral_0_name)

    DSrepair_codestral_1_name = 'intermediate_result_conversation/sota/codestral_all_0(stderr+kg+fl)/0/repair_test/ds1000_model_codestral-latest_fl_kg.json_0'
    DSrepair_codestral_1 = load_res_list(DSrepair_codestral_1_name)

    DSrepair_codestral_2_name = 'intermediate_result_conversation/sota/codestral_all_0(stderr+kg+fl)/repair_test/ds1000_model_codestral-latest_fl_kg.json_0'
    DSrepair_codestral_2 = load_res_list(DSrepair_codestral_2_name)

    input_list_gpt = [
        ['Code-Search', [code_search_gpt_0, code_search_gpt_1, code_search_gpt_2]],
        ['Chat-Repair', [stderr_gpt_0, stderr_gpt_1, stderr_gpt_2]],
        ['Self-Debugging-S', [simple_gpt_0, simple_gpt_1, simple_gpt_2]],
        ['Self-Debugging-E', [line_explanation_gpt_0, line_explanation_gpt_1, line_explanation_gpt_2], []],
        ['Self-Repair', [explanation_gpt_0, explanation_gpt_1, explanation_gpt_2], []],
        ['DSrepair', [DSrepair_gpt_0, DSrepair_gpt_1, DSrepair_gpt_2]],
    ]

    input_list_deepseek = [
        ['Code-Search', [code_search_deepseek_0, code_search_deepseek_1, code_search_deepseek_2]],
        ['Chat-Repair', [stderr_deepseek_0, stderr_deepseek_1, stderr_deepseek_2]],
        ['Self-Debugging-S', [simple_deepseek_0, simple_deepseek_1, simple_deepseek_2]],
        ['Self-Debugging-E', [line_explanation_deepseek_0, line_explanation_deepseek_1, line_explanation_deepseek_2],
         []],
        ['Self-Repair', [explanation_deepseek_0, explanation_deepseek_1, explanation_deepseek_2], []],
        ['DSrepair', [DSrepair_deepseek_0, DSrepair_deepseek_1, DSrepair_deepseek_2]],
    ]

    input_list_codestral = [
        ['Code-Search', [code_search_codestral_0, code_search_codestral_1, code_search_codestral_2]],
        ['Chat-Repair', [stderr_codestral_0, stderr_codestral_1, stderr_codestral_2]],
        ['Self-Debugging-S', [simple_codestral_0, simple_codestral_1, simple_codestral_2]],
        ['Self-Debugging-E', [line_explanation_codestral_0, line_explanation_codestral_1, line_explanation_codestral_2],
         []],
        ['Self-Repair', [explanation_codestral_0, explanation_codestral_1, explanation_codestral_2], []],
        ['DSrepair', [DSrepair_codestral_0, DSrepair_codestral_1, DSrepair_codestral_2]],
    ]

    for i in range(len(input_list_gpt)):
        # fixed number
        fixed_number_gpt = []
        for res_list in input_list_gpt[i][1]:
            tmp_count = 0
            for content in res_list:
                if content['returncode'] == 0:
                    tmp_count += 1
            fixed_number_gpt.append(tmp_count)
        # print(fixed_number_gpt)
        fixed_number_deepseek = []
        for res_list in input_list_deepseek[i][1]:
            tmp_count = 0
            for content in res_list:
                if content['returncode'] == 0:
                    tmp_count += 1
            fixed_number_deepseek.append(tmp_count)

        fixed_number_codestral = []
        for res_list in input_list_codestral[i][1]:
            tmp_count = 0
            for content in res_list:
                if content['returncode'] == 0:
                    tmp_count += 1
            fixed_number_codestral.append(tmp_count)
        print('%s & %s $\pm$ %s & %s $\pm$ %s & %s $\pm$ %s \\\\' % (input_list_gpt[i][0],
                                                                     round(np.mean(fixed_number_gpt), 2),
                                                                     round(np.std(fixed_number_gpt), 2),
                                                                     round(np.mean(fixed_number_deepseek), 2),
                                                                     round(np.std(fixed_number_deepseek), 2),
                                                                     round(np.mean(fixed_number_codestral), 2),
                                                                     round(np.std(fixed_number_codestral), 2),
                                                                     ))


def RQ_API_richness():
    # load data
    gpt_list = [
        ['with_explanation', with_explanation_gpt_0],
        ['with_parameter_return', with_parameter_return_gpt_1],
        ['with_explanation_parameter_return', with_explanation_parameter_return_gpt_1],
        ['DSrepair', a_local_global],
    ]

    deepseek_list = [
        ['with_explanation', with_explanation_deepseek_0],
        ['with_parameter_return', with_parameter_return_deepseek_0],
        ['with_explanation_parameter_return', with_explanation_parameter_return_deepseek_2],
        ['DSrepair', d_local_global],
    ]

    codestral_list = [
        ['with_explanation', with_explanation_codestral_0],
        ['with_parameter_return', with_parameter_return_codestral_0],
        ['with_explanation_parameter_return', with_explanation_parameter_return_codestral_0],
        ['DSrepair', c_local_global],
    ]

    input_list = [gpt_list, deepseek_list, codestral_list]
    count_fix_rate_token_usage_overall(input_list)


def RQ_compare_plain_text():
    # load data

    gpt_list = [
        ['plain_text', plain_text_gpt_0],
        ['DSrepair', a_local_global],
    ]

    deepseek_list = [
        ['plain_text', plain_text_deepseek_0],
        ['DSrepair', d_local_global],
    ]

    codestral_list = [
        ['plain_text', plain_text_codestral_0],
        ['DSrepair', c_local_global],
    ]
    input_list = [gpt_list, deepseek_list, codestral_list]
    count_fix_rate_token_usage_overall(input_list)


def draw_scatter_plot_fix_rate_and_token_usage_seperate(input_list, save=False):
    name_list = []
    figsize = (18, 8)
    fontsize_1 = 30
    fontsize_2 = 24
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    # fig.subplots_adjust(top=0.8)

    point_list_gpt = []
    point_list_deepseek = []
    point_list_codestral = []

    markers = {'Code-Search': 'o',
               'Chat-Repair': 's',
               'Self-Debugging-S': '^',
               'Self-Debugging-E': 'D',
               'Self-Repair': 'P',
               'DSrepair': '*'}
    color_gpt = '#009fb7'
    color_deepseek = '#ef476f'
    color_codestral = '#edae49'

    # Populate point lists
    for item in input_list[0]:
        tmp_fixed_number = count_fixed_number(item[1])
        fix_rate = tmp_fixed_number / 562
        if len(item) == 3:
            token_usage = sum(count_mean_token(item[1])) + sum(count_mean_token(item[2]))
        else:
            token_usage = sum(count_mean_token(item[1]))
        name_list.append(item[0])
        point_list_gpt.append((item[0], token_usage, fix_rate))

    for item in input_list[1]:
        tmp_fixed_number = count_fixed_number(item[1])
        fix_rate = tmp_fixed_number / 562
        if len(item) == 3:
            token_usage = sum(count_mean_token(item[1])) + sum(count_mean_token(item[2]))
        else:
            token_usage = sum(count_mean_token(item[1]))
        name_list.append(item[0])
        point_list_deepseek.append((item[0], token_usage, fix_rate))

    for item in input_list[2]:
        tmp_fixed_number = count_fixed_number(item[1])
        fix_rate = tmp_fixed_number / 562
        if len(item) == 3:
            token_usage = sum(count_mean_token(item[1])) + sum(count_mean_token(item[2]))
        else:
            token_usage = sum(count_mean_token(item[1]))
        name_list.append(item[0])
        point_list_codestral.append((item[0], token_usage, fix_rate))

    # Sort the lists
    # point_list_gpt = sorted(point_list_gpt, key=lambda x: x[1])
    # point_list_deepseek = sorted(point_list_deepseek, key=lambda x: x[1])
    # point_list_codestral = sorted(point_list_codestral, key=lambda x: x[1])

    scatter_handles = []

    # Plot for GPT
    ax = axes[0]
    for item in point_list_gpt:
        label = item[0]
        marker = markers[label]
        if item[0] == 'DSrepair':
            scatter_handles.append(
                ax.scatter(item[1], item[2], label=label, marker=marker, color='black', s=1500, edgecolors='black'))
            scatter = ax.scatter(item[1], item[2], label=label, marker=marker, color=color_gpt, s=1500,
                                 edgecolors='black')
        else:
            scatter_handles.append(
                ax.scatter(item[1], item[2], label=label, marker=marker, color='black', s=500))
            scatter = ax.scatter(item[1], item[2], label=label, marker=marker, color=color_gpt, s=500)

    ax.set_title('GPT-3.5-turbo', fontsize=fontsize_1)
    ax.set_xlabel('Token Usage', fontsize=fontsize_1)
    ax.set_ylabel('Fix Rate', fontsize=fontsize_1)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0, top=0.32)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.tick_params(axis='x', labelsize=fontsize_2)
    ax.tick_params(axis='y', labelsize=fontsize_2)

    # Plot for DeepSeek
    ax = axes[1]
    for item in point_list_deepseek:
        label = item[0]
        marker = markers[label]
        if item[0] == 'DSrepair':
            ax.scatter(item[1], item[2], label=label, marker=marker, color=color_deepseek, s=1500, edgecolors='black')
        else:
            ax.scatter(item[1], item[2], label=label, marker=marker, color=color_deepseek, s=500)
    ax.set_title('DeepSeek-Coder', fontsize=fontsize_1)
    ax.set_xlabel('Token Usage', fontsize=fontsize_1)
    # ax.set_ylabel('Fix Rate', fontsize=24)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0, top=0.32)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.tick_params(axis='x', labelsize=fontsize_2)
    ax.tick_params(axis='y', labelsize=fontsize_2)

    # Plot for Codestral
    ax = axes[2]
    for item in point_list_codestral:
        label = item[0]
        marker = markers[label]
        if item[0] == 'DSrepair':
            ax.scatter(item[1], item[2], label=label, marker=marker, color=color_codestral, s=1500, edgecolors='black')
        else:
            ax.scatter(item[1], item[2], label=label, marker=marker, color=color_codestral, s=500)
    ax.set_title('Codestral', fontsize=fontsize_1)
    ax.set_xlabel('Token Usage', fontsize=fontsize_1)
    # ax.set_ylabel('Fix Rate', fontsize=24)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0, top=0.32)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.tick_params(axis='x', labelsize=fontsize_2)
    ax.tick_params(axis='y', labelsize=fontsize_2)

    # Set legends
    # line_handles = [Line2D([0], [0], color=color_gpt, label='GPT-3.5-turbo'),
    #                 Line2D([0], [0], color=color_deepseek, label='DeepSeek-Coder'),
    #                 Line2D([0], [0], color=color_codestral, label='Codestral')]

    # for ax in axes:
    fig.legend(handles=scatter_handles,
               loc='upper left',
               ncol=len(scatter_handles) / 2,
               markerscale=0.6,
               fontsize=fontsize_1,
               handletextpad=0,
               bbox_to_anchor=(0.03, 1),
               columnspacing=0)

    plt.tight_layout(rect=(0, 0, 1, 0.8))
    if save:
        plt.savefig('fig/scatter_plot_token_usage_and_fix_rate_seperate.pdf')
    plt.show()


def RQ2_draw_scatter_plot_seperate(save=False):
    input_list = load_data_overall()
    draw_scatter_plot_fix_rate_and_token_usage_seperate(input_list, save)
