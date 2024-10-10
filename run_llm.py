import json
import os
import asyncio
from enrich_prompt import *
from util import *
from code_test import run_test_conversation
import time
def run_conversation(test_res_list, ds1000, option, search_res_dic, setting):
    if 'small_experiment' in option:
        repair_times = 1
    else:
        repair_times = 5
    for i in range(repair_times):
        print('repair count: %s' % (i))
        # generate message/prompt
        store_file_name_suffix = get_store_file_name_suffix(option)
        path = 'intermediate_result_conversation/ds1000%s.json_%s' % (store_file_name_suffix, i)
        if os.path.exists(path):
            id_prompt_list = []
        else:
            id_prompt_list = enrich_prompt_for_error_code(test_res_list, ds1000, i, search_res_dic, option, setting)
        # return id_prompt_list

        response_list, file_path, Done_flag = use_gpt_model_repair(id_prompt_list, option, store_file_name_suffix, setting, i)
        # test the response
        # Done_flag = False
        test_res_file_path = run_test_conversation(response_list, file_path, Done_flag)
        # update test_res_list, search_res_dic
        test_res_list, search_res_dic = update_conversation(test_res_file_path, ds1000, option, i)
    return test_res_list

def update_conversation(test_res_file_path, ds1000, option, i):
    test_res_list = []
    search_res_dic = {}
    print('Updating test_res_list')
    with open(test_res_file_path, 'r') as f:
        for line in f.readlines():
            test_res_list.append(json.loads(line))
    error_res_list = filter_error_problem(test_res_list, ds1000)
    print('Updating search_res_dic')
    if option['code_search']:
        tmp_file = 'code_search_lucene/error_res_list.json_%s' % i
        if not os.path.exists(tmp_file):
            with open(tmp_file, 'w') as f:
                for res in error_res_list:
                    new_res = query_type_enrich_res(res, option, ds1000)
                    f.write(json.dumps(new_res)+'\n')
        search_res_dic = {}
        with open('intermediate_result_conversation/query2code.txt_%s' % (i), 'r') as f:
            for line in f.readlines():
                content = json.loads(line)
                search_res_dic[content['pid']] = {
                    'prompt': content['prompt'],
                    'search_result': search_database(content['search_result'])
                }

    print('ALL DONE updating')
    return error_res_list, search_res_dic


def run_base(test_res_list, ds1000, option, search_res_dic, setting):
    id_prompt_list = enrich_prompt_for_error_code(test_res_list, ds1000, search_res_dic, option, setting)
    # return id_prompt_list
    store_file_name_suffix = get_store_file_name_suffix(option)
    if 'gpt' in option['model']:
        # close-source models, e.g. gpt-3.5-turbo, deepseek-coder, codestral
        result_list = use_gpt_model_repair(id_prompt_list, option, store_file_name_suffix, setting)
    else:
        result_list = []
    return result_list


def use_gpt_model_repair(id_prompt_list, option, store_file_name_suffix, setting, con_id=0):
    result_list = []
    Done_flag = False
    if option['conversation']:
        path = 'intermediate_result_conversation/ds1000%s.json_%s' % (store_file_name_suffix, con_id)
        if os.path.exists(path):
            Done_flag = True
            with open(path, 'r') as f:
                res_list = json.load(f)
            # path = 'intermediate_result_conversation/ds1000%s.json' % (store_file_name_suffix)
        else:
            if 'codestral' in option['model']:
                res_list = []
                for id_prompt in id_prompt_list:
                    tmp_res_list = asyncio.run(openai_model_conversation([id_prompt], setting))
                    res_list.append(tmp_res_list[0])
                    time.sleep(0.2)
            else:
                res_list = asyncio.run(openai_model_conversation(id_prompt_list, setting))
            with open(path, 'w') as f:
                f.write(json.dumps(res_list))
        return res_list, path, Done_flag
    else:
        for i in range(5):
            # run the experiment 5 times to mitigate randomness
            path = 'intermediate_result/ds1000%s.json_%s' % (store_file_name_suffix, i)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    res_list = json.load(f)
            else:
                # if option['conversation']:
                #     # should be message
                #     else:
                res_list = asyncio.run(openai_model_repair(id_prompt_list, setting))
                with open(path, 'w') as f:
                    f.write(json.dumps(res_list))
            result_list.append(res_list)
            # run_stderr = run_runability_test(res_list, ds1000)
    return result_list

def run_ChatGPT(data_dic, option, setting):
    test_res_list = data_dic['test_res_list']

    if 'search_res_dic' in data_dic:
        search_res_dic = data_dic['search_res_dic']
    else:
        search_res_dic = {}

    ds1000 = data_dic['ds1000']
    if not option['conversation']:
        result_list = run_base(test_res_list, ds1000, option, search_res_dic, setting)
    else:
        result_list = run_conversation(test_res_list, ds1000, option, search_res_dic, setting)

    return result_list


def get_store_file_name_suffix(option):
    store_file_name_suffix = ''
    # store_file_name_suffix += '_dataset_' + option['dataset']
    store_file_name_suffix += '_model_' + option['model']
    if option['code_search']:
        store_file_name_suffix += '_code_search'
        return store_file_name_suffix
    if option['fault_localization']:
        store_file_name_suffix += '_fl'
        if option['kg']:
            store_file_name_suffix += '_kg'
        return store_file_name_suffix
    # if option['baseline']:
    #     store_file_name_suffix += '_baseline'
    # else:
    if option['stderr_only']:
        store_file_name_suffix += '_stderr'
    elif option['triplet_only']:
        store_file_name_suffix += '_triplet'
        if option['natural_language']:
            store_file_name_suffix += '_natural_language'
    else:
        if option['stderr_first']:
            store_file_name_suffix += '_stderr_triplet'
            if option['natural_language']:
                store_file_name_suffix += '_natural_language'
        else:
            store_file_name_suffix += '_triplet_stderr'
            if option['natural_language']:
                store_file_name_suffix += '_natural_language'
    if option['conversation']:
            store_file_name_suffix += '_conversation'
    if (not option['triplet_only']) and (not option['conversation']) and option['with_bug_code']:
        store_file_name_suffix += '_with_bug_code'
    if option['filter_out']:
        store_file_name_suffix += '_filter_out'
    for item in option['filter_out']:
        store_file_name_suffix += '_' + item
    return store_file_name_suffix

def run_experiment(data_dic, option):
    setting = {
        'model': option['model'], # gpt-3.5-turbo-0125
        'instruction_prompt': 'Generate Python3 code ended with \'</code>\\nEND SOLUTION\'\n',
        'temperature': 0,
    }
    if 'gpt' in option['model'] or 'deepseek' in option['model'] or 'codestral' in option['model']:
        a = run_ChatGPT(data_dic, option, setting)
    return a