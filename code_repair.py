import os.path
from code_generation import *
from run_llm import run_experiment
from util import *

def load_option(setting_name, model):
    option = {}
    filter_out = []
    if setting_name == 'Code_Search':
        option = {
            'code_search': True,
            'code_search_query_type': 'prompt',
            'conversation': True,
            'baseline': False,
            'model': model,
            'stderr_only': True,
            'triplet_only': False,
            'natural_language': True,
            'stderr_first': True,
            'with_bug_code': False,
            'filter_out': filter_out,
            'fault_localization': False,
            'kg': False,
            'classifier': False,
            'small_experiment': True
        }
    elif setting_name == 'DSrepair':
        option = {
            'code_search': False,
            'conversation': True,
            'baseline': False,
            'model': model,
            'stderr_only': True,
            'triplet_only': False,
            'natural_language': True,
            'stderr_first': True,
            'with_bug_code': False,
            'filter_out': filter_out,
            'small_experiment': True,
            'fault_localization': True,
            'kg': True,
            'classifier': False
        }
    elif setting_name == 'Debugging_S':
        option = {
            'simple_feedback': True,
            'code_search': False,
            'conversation': True,
            'baseline': False,
            'model': model,
            'stderr_only': False,
            'triplet_only': False,
            'natural_language': False,
            'stderr_first': False,
            'with_bug_code': False,
            'filter_out': filter_out,
            'small_experiment': False,
            'fault_localization': False,
            'kg': False,
            'classifier': False
        }
    elif setting_name == 'Chat_Repair':
        option = {
            'code_search': False,
            'conversation': True,
            'baseline': False,
            'model': model,
            'stderr_only': True,
            'triplet_only': False,
            'natural_language': True,
            'stderr_first': False,
            'with_bug_code': False,
            'filter_out': filter_out,
            'small_experiment': True,
            'fault_localization': False,
            'kg': False,
            'classifier': False
        }
    elif setting_name == 'Self_Repair':
        option = {
            'explanation': True,
            'code_search': False,
            'conversation': True,
            'baseline': False,
            'model': model,
            'stderr_only': False,
            'triplet_only': False,
            'natural_language': False,
            'stderr_first': False,
            'with_bug_code': False,
            'filter_out': filter_out,
            'small_experiment': False,
            'fault_localization': False,
            'kg': False,
            'classifier': False
        }
    elif setting_name == 'Debugging_S':
        option = {
            'line_explanation': True,
            'code_search': False,
            'conversation': True,
            'baseline': False,
            'model': model,
            'stderr_only': False,
            'triplet_only': False,
            'natural_language': False,
            'stderr_first': False,
            'with_bug_code': False,
            'filter_out': filter_out,
            'small_experiment': False,
            'fault_localization': False,
            'kg': False,
            'classifier': False
        }
    elif setting_name == 'Plain_Text':
        option = {
            'code_search': False,
            'conversation': True,
            'baseline': False,
            'model': model,
            'stderr_only': True,
            'triplet_only': False,
            'natural_language': True,
            'stderr_first': True,
            'with_bug_code': False,
            'filter_out': filter_out,
            'small_experiment': True,
            'fault_localization': True,
            'kg': True,
            'classifier': False,
            'plain_text': True
        }
    return option


def code_repair_KG(test_res_list, option_name, model='gpt-3.5-turbo'):
    filter_out = []

    option = load_option(option_name, model)
    if option['code_search']:
        search_res_dic = {}
        tmp_file = './code_search_lucene/error_res_list.json_initial'
        if not os.path.exists(tmp_file):
            with open(tmp_file, 'w') as f:
                for res in test_res_list:
                    new_res = query_type_enrich_res(res, option, ds1000)
                    f.write(json.dumps(new_res)+'\n')

        if option['conversation']:
            with open('experiment_result/query2code.txt_initial', 'r') as f:
                for line in f.readlines():
                    content = json.loads(line)
                    search_res_dic[content['pid']] = {
                        'prompt': content['prompt'],
                        'search_result': search_database(content['search_result'])
                    }
        else:
            with open('intermediate_result/query2code.txt_initial', 'r') as f:
                for line in f.readlines():
                    content = json.loads(line)
                    search_res_dic[content['pid']] = {
                        'prompt': content['prompt'],
                        'search_result': search_database(content['search_result'])
                    }
        data_dic = {
            'test_res_list': test_res_list,
            'ds1000': ds1000,
            'search_res_dic': search_res_dic
        }
    elif option['baseline'] or option['stderr_only']:
        data_dic = {
            'test_res_list': test_res_list,
            'ds1000': ds1000
        }
    else:
        data_dic = {
            'test_res_list': test_res_list,
            'html_kg_toolkit_dic': {},
            'ds1000': ds1000
        }
    print('Done loading html kg_repair toolkit!')
    result_list_html = run_experiment(data_dic, option)
    return result_list_html


if __name__ == "__main__":

    target_file = 'ds1000_t_0.json'
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000_new.jsonl.gz", "rt").readlines()]
    first_test_res_list = []
    with open('intermediate_result/first_test/enriched_' + target_file, 'r') as f:
        for line in f.readlines():
            first_test_res_list.append(json.loads(line))
    error_res_list = filter_error_problem(first_test_res_list, ds1000)

    # model = 'codestral-latest'
    # model = 'deepseek-coder'
    model = 'gpt-3.5-turbo'
    a = code_repair_KG(error_res_list, 'Debugging_S', model)
