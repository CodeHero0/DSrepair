import ast
import json
import os.path
import re
from pprint import pprint
from util import *
import kg_api
import tiktoken
from bug_enrichment import get_bug_info
import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize


def extract_error_and_following_lines(stderr):
    # Use regex to find the line with "Error:" and capture the rest of the lines
    match = re.search(r'(.*Error.*\n(?:.*\n)*)', stderr, re.MULTILINE)
    if match:
        return match.group(1)
    return stderr
def mask_the_local_info(stderr_info):
    local_info1 = ''
    local_info2 = ''


    new_stderr = 'Traceback (most recent call last):\n' + stderr_info.split('Traceback (most recent call last):')[-1]


    if local_info1 in new_stderr or local_info2 in new_stderr:
        return new_stderr.replace(local_info1, '').replace(local_info2, '')
    else:
        return new_stderr

def enrich_prompt_with_stderr(message, stderr, original_prompt, generated_code, setting, conversation=False, natural_language=False, with_bug_code=False):
    # natural language not work for stderr
    prompt = ''
    if with_bug_code:
        prompt += 'The incorrect code example is:\n%s\n' % (generated_code)
        prompt += 'which has the following error:\n'
    else:
        prompt += 'Avoid the generated code that has the following error:\n'
    prompt += mask_the_local_info(stderr) + '\n'
    prompt += 'Correct the code using the provided information.\n'

    # return original_prompt + '\n'+ prompt.strip()
    if conversation:
        prompt += setting['instruction_prompt']
        new_message = []
        new_message += message
        new_message.append({"role": "assistant", "content": generated_code +'\n</code>\nEND SOLUTION'}),
        new_message.append({"role": "user", "content": prompt}),
        return new_message
    else:
        return prompt + '\n' + original_prompt

def triplets2natural_language(triplets):
    namespace = ''
    if triplets:
        if 'https://numpy-code.org/' in triplets[0][0]:
            namespace = 'https://numpy-code.org/'
        elif 'https://numpy-html.org/' in triplets[0][0]:
            namespace = 'https://numpy-html.org/'

    triplet_natural_language = triplet_list2natural_language(triplets, namespace)
    return triplet_natural_language

def enrich_prompt_with_triplets(query_result_list, original_prompt, conversation=False, natural_language=True):
    # prompt = ''
    if natural_language:
        prompt = 'The generated code might need the following API library knowledge:\n'
    else:
        prompt = 'The generated code might need the following API library knowledge that stored in RDF triplets:\n'
    if natural_language:
        # prompt += triplets2natural_language(triplets)
        prompt += query_result_list2natural_language(query_result_list)
        prompt += '\nIt is not necessary to use the above API library knowledge to generate code. Other ways to generated the code are also recommanded.\n'
    # else:
    #     for triplet in triplets:
    #         prompt += '<%s, %s, %s>\n' % (triplet[0].split('/')[-1], triplet[1].split('/')[-1], triplet[2].split('/')[-1])
    if conversation:
        return prompt
    else:
        return prompt + '\n' + original_prompt

def enrich_prompt_with_stderr_and_triplets(query_result_list, message, stderr, original_prompt, generated_code, conversation=False, natural_language=True, stderr_first=True, with_bug_code=False, setting={}):
    if with_bug_code:
        prompt_stderr = 'The incorrect code example is:\n%s\n' % (generated_code)
        prompt_stderr += 'which has the following error:\n'
    else:
        prompt_stderr = 'Avoid the generated code has the following error:\n'
    if natural_language:
        prompt_triplet = 'The generated code might need the following API library knowledge:\n'
    else:
        prompt_triplet = 'The generated code might need the following API library knowledge that stored in RDF triplets:\n'
    prompt = ''
    if natural_language:
        if stderr_first:
            prompt += prompt_stderr
            prompt += mask_the_local_info(stderr) + '\n'
            prompt += prompt_triplet
            # prompt += triplets2natural_language(triplets)
            prompt += query_result_list2natural_language(query_result_list)
            prompt += '\nIt is not necessary to use the above API library knowledge to generate code. Other ways to generated the code are also recommended.\n'
        else:
            prompt += prompt_triplet
            # prompt += triplets2natural_language(triplets)
            prompt += query_result_list2natural_language(query_result_list)
            prompt += '\nIt is not necessary to use the above API library knowledge to generate code. Other ways to generated the code are also recommended.\n'
            prompt += prompt_stderr
            prompt += mask_the_local_info(stderr) + '\n'
    # else:
    #     if stderr_first:
    #         prompt += prompt_stderr
    #         prompt += mask_the_local_info(stderr) + '\n'
    #         prompt += prompt_triplet
    #         for triplet in triplets:
    #             prompt += '<%s, %s, %s>\n' % (triplet[0].split('/')[-1], triplet[1].split('/')[-1], triplet[2].split('/')[-1])
    #     else:
    #         prompt += prompt_triplet
    #         for triplet in triplets:
    #             prompt += '<%s, %s, %s>\n' % (triplet[0].split('/')[-1], triplet[1].split('/')[-1], triplet[2].split('/')[-1])
    #         prompt += prompt_stderr
    #         prompt += mask_the_local_info(stderr) + '\n'

    if conversation:
        prompt += setting['instruction_prompt']
        new_message = []
        new_message += message
        new_message.append({"role": "assistant", "content": generated_code+'\n</code>\nEND SOLUTION'}),
        new_message.append({"role": "user", "content": prompt}),
        return new_message
    else:
        return prompt + '\n' + original_prompt
    # return prompt + '\n' + original_prompt

def enrich_prompt_with_search_result(pid, message, generated_code, search_result_dic, original_prompt, option, conversation=False, setting={}, limit=10):
    prompt_code_search = ''

    if option['code_search_query_type'] == 'full_expression':
        prompt_code_search += 'The generated incorrect code use some library functions. Below are the source implementation of these functions:\n'
        count = 0
        for item in search_result_dic[pid]['search_result']:
            if count >= limit:
                break
            exemplar = item['exemplar']
            prompt_code_search += '[Source Code]\n' + exemplar + '\n'

            count += 1
        prompt_code_search += 'Please use the above code as reference (do not contain source code in code generation) to figure out why the generated code is incorrect, and regenerate the code\n'

    else:
        prompt_code_search += 'The generated code might need the following exemplar that stored in the codebase:\n'
        count = 0
        for item in search_result_dic[pid]['search_result']:
            if count >= limit:
                break
            exemplar = item['exemplar']
            prompt_code_search += '[Exemplar]\n' + exemplar + '\n'
            count += 1
    prompt_code_search += setting['instruction_prompt']

    if conversation:
        new_message = []
        new_message += message
        new_message.append({"role": "assistant", "content": generated_code+'\n</code>\nEND SOLUTION'}),
        new_message.append({"role": "user", "content": prompt_code_search}),
        return new_message
    else:
        return prompt_code_search + '\n' + original_prompt


def enrich_prompt_with_stderr_search_result(pid, message, stderr, generated_code, search_result_dic, original_prompt, option, conversation=False, setting={}, limit=10):
    prompt_code_search = '###\nAvoid the generated code that has the following error:\n'

    prompt_code_search += mask_the_local_info(stderr) + '\n'

    if option['code_search_query_type'] == 'full_expression':
        prompt_code_search += '###\nThe generated incorrect code use some library functions. Below are the source implementation of these functions:\n'
        count = 0
        for item in search_result_dic[pid]['search_result']:
            if count >= limit:
                break
            exemplar = item['exemplar']
            prompt_code_search += '[Source Code]\n' + exemplar + '\n'

            count += 1
        prompt_code_search += '###\nPlease use the above code as reference (do not contain source code in code generation) to figure out why the generated code is incorrect, and regenerate the code\n'

    else:
        prompt_code_search += '###\nThe generated code might need the following exemplar that stored in the codebase:\n'
        count = 0
        for item in search_result_dic[pid]['search_result']:
            if count >= limit:
                break
            exemplar = item['exemplar']
            prompt_code_search += '[Exemplar]\n' + exemplar + '\n'
            count += 1
        prompt_code_search += '###\n' + setting['instruction_prompt']

    if conversation:
        new_message = []
        new_message += message
        new_message.append({"role": "assistant", "content": generated_code+'\n</code>\nEND SOLUTION'}),
        new_message.append({"role": "user", "content": prompt_code_search}),
        return new_message
    else:
        return prompt_code_search + '\n' + original_prompt


def get_kg_classifier_dic(error_res_list, ds1000, repair_index, classifier='direct_classifier'):
    # request
    setting = {
        'model': 'gpt-3.5-turbo',  # gpt-3.5-turbo-0125
        'instruction_prompt': 'Generate Python3 code ended with \'</code>\\nEND SOLUTION\'\n',
        'temperature': 0,
        'classifier_type': classifier
    }
    stored_folder_path = 'intermediate_result_conversation/function_suggestion/'
    if not os.path.exists(stored_folder_path):
        os.makedirs(stored_folder_path)

    if os.path.exists(stored_folder_path + 'numpy_error_%s_%s' % (setting['classifier_type'], repair_index) + '.json'):
        with open(stored_folder_path + 'numpy_error_%s_%s' % (setting['classifier_type'], repair_index) + '.json', 'r') as f:
            classifier_res_list = json.load(f)
        print('Existed classifier...')
    else:
        print('Generate new classifier...')
        classifier_res_list = asyncio.run(openai_model_classifier(ds1000, error_res_list, setting=setting))
        # if not os.path.exists(stored_folder_path + stored_file_name + '.json'):
        with open(stored_folder_path + 'numpy_error_%s_%s' % (setting['classifier_type'], repair_index) + '.json', 'w') as f:
            f.write(json.dumps(classifier_res_list))

    final_suggestion_dic = {}
    for res in classifier_res_list:
        try:
            tmp_res = eval(res['response'])
        except:
            tmp_res = False

        if tmp_res == True:
            final_suggestion_dic[res['pid']] = True
        else:
            final_suggestion_dic[res['pid']] = False

    return final_suggestion_dic


def generate_explanation_for_repair(error_res_list, ds1000, repair_index, model):
    setting = {
        'model': model,  # gpt-3.5-turbo-0125
        'instruction_prompt': 'Generate Python3 code ended with \'</code>\\nEND SOLUTION\'\n',
        'temperature': 0,
    }
    stored_folder_path = 'intermediate_result_conversation/explanation/'
    if not os.path.exists(stored_folder_path):
        os.makedirs(stored_folder_path)

    if os.path.exists(stored_folder_path + 'explanation_%s' % (repair_index) + '.json'):
        with open(stored_folder_path + 'explanation_%s' % (repair_index) + '.json', 'r') as f:
            explanation_res_list = json.load(f)
        print('Existed explanation...')
    else:
        print('Generate new explanation...')
        explanation_res_list = asyncio.run(openai_model_explanation(ds1000, error_res_list, setting=setting))
        # if not os.path.exists(stored_folder_path + stored_file_name + '.json'):
        with open(stored_folder_path + 'explanation_%s' % (repair_index) + '.json', 'w') as f:
            f.write(json.dumps(explanation_res_list))
        print('Done!')

    final_explanation_dic = {}
    for res in explanation_res_list:
        final_explanation_dic[res['pid']] = res['response']
    return final_explanation_dic

def generate_line_explanation_for_repair(error_res_list, ds1000, repair_index):
    setting = {
        'model': 'gpt-3.5-turbo',  # gpt-3.5-turbo-0125
        'instruction_prompt': 'Generate Python3 code ended with \'</code>\\nEND SOLUTION\'\n',
        'temperature': 0,
        'explanation_type': 'line_explanation',
    }
    stored_folder_path = 'intermediate_result_conversation/line_explanation/'
    if not os.path.exists(stored_folder_path):
        os.makedirs(stored_folder_path)

    if os.path.exists(stored_folder_path + 'line_explanation_%s' % (repair_index) + '.json'):
        with open(stored_folder_path + 'line_explanation_%s' % (repair_index) + '.json', 'r') as f:
            explanation_res_list = json.load(f)
        print('Existed line_explanation...')
    else:
        print('Generate new line_explanation...')
        explanation_res_list = asyncio.run(openai_model_explanation(ds1000, error_res_list, setting=setting))
        # if not os.path.exists(stored_folder_path + stored_file_name + '.json'):
        with open(stored_folder_path + 'line_explanation_%s' % (repair_index) + '.json', 'w') as f:
            f.write(json.dumps(explanation_res_list))

    final_explanation_dic = {}
    for res in explanation_res_list:
        final_explanation_dic[res['pid']] = res['response']
    return final_explanation_dic

def get_kg_info_tensorflow(pid):
    if pid == 669:
        tmp_nl = 'tf.one_hot(indices,depth,on_value=None,off_value=None,axis=None,dtype=None,name=None)\n'
    elif pid == 670:
        tmp_nl = 'tf.one_hot(indices,depth,on_value=None,off_value=None,axis=None,dtype=None,name=None)\n'
    elif pid == 671:
        tmp_nl = 'tf.one_hot(indices,depth,on_value=None,off_value=None,axis=None,dtype=None,name=None)\n'
    elif pid == 672:
        tmp_nl = 'tf.one_hot(indices,depth,on_value=None,off_value=None,axis=None,dtype=None,name=None)\n'
    elif pid == 677:
        tmp_nl = 'tf.sequence_mask(lengths,maxlen=None,dtype=tf.dtypes.bool,name=None)\n'
    elif pid == 679:
        tmp_nl = ('tf.sequence_mask(lengths,maxlen=None,dtype=tf.dtypes.bool,name=None)\n' +
                  'tf.reverse( tensor: Annotated[Any, TV_ReverseV2_T], axis: Annotated[Any, TV_ReverseV2_Tidx], name=None ) -> Annotated[Any, TV_ReverseV2_T]\n')
    elif pid == 681:
        tmp_nl = ('tf.expand_dims( input, axis, name=None )\n' +
                  'tf.reshape( tensor, shape, name=None )\n' +
                  'tf.concat( values, axis, name=\'concat\' )\n')
    elif pid == 684:
        tmp_nl = 'tf.reshape( tensor, shape, name=None )\n'
    elif pid == 688:
        tmp_nl = ('tf.math.reduce_sum( input_tensor, axis=None, keepdims=False, name=None )\n' +
                  'tf.math.square( x: Annotated[Any, tf.raw_ops.Any], name=None ) -> Annotated[Any, tf.raw_ops.Any]\n' +
                  'tf.math.subtract( x, y, name=None )\n')
    elif pid == 690:
        tmp_nl = (
                'tf.math.square( x: Annotated[Any, tf.raw_ops.Any], name=None ) -> Annotated[Any, tf.raw_ops.Any]\n' +
                'tf.math.subtract( x, y, name=None )\n' +
                'tf.math.reduce_sum( input_tensor, axis=None, keepdims=False, name=None )\n')
    elif pid == 691:
        tmp_nl = ('tf.gather_nd( params, indices, batch_dims=0, name=None )\n' +
                  'tf.stack( values, axis=0, name=\'stack\' )\n')
    elif pid == 692:
        tmp_nl = ('tf.gather_nd( params, indices, batch_dims=0, name=None )\n' +
                  'tf.stack( values, axis=0, name=\'stack\' )\n')
    elif pid == 693:
        tmp_nl = ('tf.gather_nd( params, indices, batch_dims=0, name=None )\n' +
                  'tf.stack( values, axis=0, name=\'stack\' )\n')
    elif pid == 694:
        tmp_nl = ('tf.tensordot( a, b, axes, name=None )\n' +
                  'tf.transpose( a, perm=None, conjugate=False, name=\'transpose\' )\n')
    elif pid == 696:
        tmp_nl = 'tf.strings.unicode_decode(input,input_encoding,errors=\'replace\',replacement_char=65533,replace_control_characters=False,name=None)\n'
    elif pid == 697:
        tmp_nl = 'tf.strings.unicode_decode(input,input_encoding,errors=\'replace\',replacement_char=65533,replace_control_characters=False,name=None)\n'
    elif pid == 698:
        tmp_nl = ('tf.math.count_nonzero(input,axis=None,keepdims=None,dtype=tf.dtypes.int64,name=None)\n' +
                  'tf.math.reduce_sum( input_tensor, axis=None, keepdims=False, name=None )\n')
    elif pid == 699:
        tmp_nl = ('tf.cast( x, dtype, name=None )\n' +
                  'tf.math.reduce_sum( input_tensor, axis=None, keepdims=False, name=None )\n' +
                  'tf.expand_dims( input, axis, name=None )\n')
    elif pid == 700:
        tmp_nl = ('tf.math.count_nonzero(input,axis=None,keepdims=None,dtype=tf.dtypes.int64,name=None)\n' +
                  'tf.math.reduce_sum( input_tensor, axis=None, keepdims=False, name=None )\n')
    elif pid == 701:
        tmp_nl = ('tf.math.reduce_sum( input_tensor, axis=None, keepdims=False, name=None )\n' +
                  'tf.linalg.matmul(a,b,transpose_a=False,transpose_b=False,adjoint_a=False,adjoint_b=False,a_is_sparse=False,b_is_sparse=False,output_type=None,grad_a=False,grad_b=False,name=None)\n')
    elif pid == 703:
        tmp_nl = 'tf.math.argmax(input,axis=None,output_type=tf.dtypes.int64,name=None)\n'
    elif pid == 704:
        tmp_nl = 'tf.math.argmax(input,axis=None,output_type=tf.dtypes.int64,name=None)\n'
    elif pid == 706:
        tmp_nl = ''
    elif pid == 709:
        tmp_nl = ('tf.random.set_seed(seed)\n' +
                  'tf.random.uniform(shape,minval=0,maxval=None,dtype=tf.dtypes.float32,seed=None,name=None)\n')
    else:
        return
    return tmp_nl

def enrich_prompt_with_kg_fault_localization(ds1000, pid, message, stderr, generated_code, original_prompt, option, plain_text_dic={}, conversation=False, setting={}):
    # prompt_kg_fl = 'The generated code is incorrect.\n'
    co_star = True
    if co_star:
        prompt_kg_fl = ''
        prompt_kg_fl += '# Problem Description #\n'
        prompt_kg_fl += ds1000[pid]['prompt'] + '\n'
        prompt_kg_fl += '##########\n\n'

        prompt_kg_fl += '# Incorrect Code #\n'
        prompt_kg_fl += generated_code + '\n'
        prompt_kg_fl += '##########\n\n'

        prompt_kg_fl += '# Stderr #\n'
        prompt_kg_fl += stderr + '\n'
        prompt_kg_fl += '##########\n\n'

        fault_localization_res = get_bug_info(pid, generated_code)

        library_name_list, special_name_list, import_lib_dic = get_library_alains(ds1000, pid)
        function_name_list = get_function_name_in_code_line(generated_code, library_name_list, special_name_list,
                                                            import_lib_dic)
        function_name_list = list(set(function_name_list))
        print(library_name_list, special_name_list, import_lib_dic)
        print(function_name_list)

        # kg
        # if not classifier_flag_dic:
        if 'plain_text' not in option:
            error_function_triplet_dic = load_kg_info(function_name_list, ds1000, pid)

            query_result_list = []
            if error_function_triplet_dic:
                for error_function_name in error_function_triplet_dic:
                    # html_triplets += error_res['error_function_triplet_dic'][error_function_name]['html_triplets']
                    query_result_list.append(error_function_triplet_dic[error_function_name]['html_triplets'])
            tmp_nl = query_result_list2natural_language(query_result_list)
            ###############
            if get_kg_info_tensorflow(pid):
                tmp_nl = get_kg_info_tensorflow(pid)
            ###############
            if tmp_nl.strip():
                prompt_kg_fl += '# API Knowledge #\n'
                prompt_kg_fl += tmp_nl + '\n'
                prompt_kg_fl += '##########\n\n'
        else:
            # with open('knowledge_graph/plain_text.json', 'r') as f:
            #     plain_text_dic = json.load(f)
            tmp_nl = ''
            for function_name in function_name_list:
                search_res = search_context_based_on_keyword(function_name,
                                                             plain_text_dic[ds1000[pid]['metadata']['library'].lower()],
                                                             ds1000[pid]['metadata']['library'].lower())
                if search_res:
                    tmp_nl += search_res[0] + '\n'
            if tmp_nl.strip():
                prompt_kg_fl += '# API Knowledge #\n'
                prompt_kg_fl += tmp_nl + '\n'
                prompt_kg_fl += '##########\n\n'


        # fault localization
        if fault_localization_res['test_case']:
            prompt_kg_fl += ('# Fault localization #\n')
            prompt_kg_fl += 'Given the example in the prompt:\n'
            prompt_kg_fl += 'Test case:\n'
            for test_case in fault_localization_res['test_case']:
                prompt_kg_fl += 'Input: %s\nOutput:%s\n' % (test_case['input'], test_case['output'])
            if 'ans_dict' in fault_localization_res['result_dict']:
                prompt_kg_fl += 'The generated code has an error at %s, and the last executable part is %s, whose value is %s\n' % (
                    fault_localization_res['last_unexec_part'],
                    fault_localization_res['last_exec_part'],
                    fault_localization_res['last_exec_part_value'],
                )
            prompt_kg_fl += '##########\n\n'

            prompt_kg_fl += ('# Fact Checking #\n')
            prompt_kg_fl += 'The generated code violated the logic stated in the description:\n%s\n' % (
                ds1000[pid]['prompt'].split('A:\n<code>')[0].strip())
            prompt_kg_fl += '##########\n\n'


        exec_environment = {}

        exec(ds1000[pid]['code_context'], {}, exec_environment)
        exec_context = exec_environment['exec_context']


        prompt_kg_fl += '# Response #\n'
        prompt_kg_fl += 'Please repair the code and generate correct Python3 code that can replace [insert] in the following test suit:\n%s\n' % (
            exec_context)
        prompt_kg_fl += '##########'


        if conversation:
            new_message = [
                {"role": "system", "content": 'You are a helpful programming assistant. '
                                              'You are helping a user write a program to solve a problem. '
                                              'The user has written some code, but it has some errors and is not passing the tests.'
                                              'Please use the information provided to generate the correct code.'}
            ]
            new_message.append({"role": "user", "content": prompt_kg_fl}),
            return new_message, len(function_name_list)
        else:
            return prompt_kg_fl

    else:
        prompt_kg_fl = ''
        if option['stderr_only']:
            prompt_kg_fl += '###\nAvoid the generated code that has the following error:\n'
            prompt_kg_fl += mask_the_local_info(stderr) + '\n'


        fault_localization_res = get_bug_info(pid, generated_code)

        library_name_list, special_name_list, import_lib_dic = get_library_alains(ds1000, pid)
        function_name_list = get_function_name_in_code_line(generated_code, library_name_list, special_name_list, import_lib_dic)
        function_name_list = list(set(function_name_list))
        print(library_name_list, special_name_list, import_lib_dic)
        print(function_name_list)
        # kg_classifier_flag = kg_classifier(pid, function_name_list, ds1000[pid]['metadata']['library'].lower())
        # print(kg_classifier_flag)

        error_function_triplet_dic = load_kg_info(function_name_list, ds1000, pid)

        query_result_list = []
        if error_function_triplet_dic:
            for error_function_name in error_function_triplet_dic:
                # html_triplets += error_res['error_function_triplet_dic'][error_function_name]['html_triplets']
                query_result_list.append(error_function_triplet_dic[error_function_name]['html_triplets'])
        tmp_nl = query_result_list2natural_language(query_result_list)
        ###############
        if get_kg_info_tensorflow(pid):
            tmp_nl = get_kg_info_tensorflow(pid)
        ###############
        if tmp_nl.strip():
            prompt_kg_fl += ('###\nBelow are the API function used in generated code:\n')
            prompt_kg_fl += tmp_nl


        # fault localization
        if fault_localization_res['test_case']:
            prompt_kg_fl += ('###\nBelow are the detailed error information for the generated code:\n')
            prompt_kg_fl += 'Given the example in the prompt:\n'
            prompt_kg_fl += 'Test case:\n'
            for test_case in fault_localization_res['test_case']:
                prompt_kg_fl += 'Input: %s\nOutput:%s\n' % (test_case['input'], test_case['output'])
            if 'ans_dict' in fault_localization_res['result_dict']:
                prompt_kg_fl += 'The generated code has an error at %s, and the last executable part is %s, whose value is %s\n' % (
                    fault_localization_res['last_unexec_part'],
                    fault_localization_res['last_exec_part'],
                    fault_localization_res['last_exec_part_value'],
                )
            prompt_kg_fl += 'The generated code violated the logic stated in the description:\n%s\n' % (ds1000[pid]['prompt'].split('A:\n<code>')[0].strip())

        exec_environment = {}
        # print(solution)
        # Execute the script within the defined scope
        exec(ds1000[pid]['code_context'], {}, exec_environment)
        exec_context = exec_environment['exec_context']
        head = 'The generated code is incorrect.\n'
        # additional = '\n###\nPlease also focus on whether the generated code\'s intention aligned with the code problem description.\n'
        # instruction = 'Please repair the code and generate correct Python3 code that can replace [insert] in the following test suit and also store the result into \'result\' variable:\n%s\n' % (exec_context)
        instruction = 'Please repair the code and generate correct Python3 code that can replace [insert] in the following test suit:\n%s\n' % (exec_context)

        if conversation:
            new_message = []
            new_message.append({"role": "user", "content": ds1000[pid]['prompt']})
            new_message.append({"role": "assistant", "content": generated_code}),
            new_message.append({"role": "user", "content": head + prompt_kg_fl + '\n###\n' + instruction}),
            # new_message.append({"role": "user", "content": head + prompt_kg_fl + '\n###\n' + setting['instruction_prompt']}),
            return new_message
        else:
            return setting['instruction_prompt'] +original_prompt + '\n\n' + head + generated_code + '\n' + prompt_kg_fl
            # return prompt_kg_fl + '\n' + original_prompt

def enrich_prompt_with_fault_localization(ds1000, pid, message, stderr, generated_code, original_prompt, option, conversation=False, setting={}):
    # prompt_kg_fl = 'The generated code is incorrect.\n'
    co_star = True
    if co_star:
        prompt_fl = ''
        prompt_fl += '# Problem Description #\n'
        prompt_fl += ds1000[pid]['prompt'] + '\n'
        prompt_fl += '##########\n\n'

        prompt_fl += '# Incorrect Code #\n'
        prompt_fl += generated_code + '\n'
        prompt_fl += '##########\n\n'

        prompt_fl += '# Stderr #\n'
        prompt_fl += stderr + '\n'
        prompt_fl += '##########\n\n'

        fault_localization_res = get_bug_info(pid, generated_code)

        library_name_list, special_name_list, import_lib_dic = get_library_alains(ds1000, pid)
        function_name_list = get_function_name_in_code_line(generated_code, library_name_list, special_name_list,
                                                            import_lib_dic)
        function_name_list = list(set(function_name_list))
        print(library_name_list, special_name_list, import_lib_dic)
        print(function_name_list)

        # fault localization
        if fault_localization_res['test_case']:
            prompt_fl += ('# Fault localization #\n')
            prompt_fl += 'Given the example in the prompt:\n'
            prompt_fl += 'Test case:\n'
            for test_case in fault_localization_res['test_case']:
                prompt_fl += 'Input: %s\nOutput:%s\n' % (test_case['input'], test_case['output'])
            if 'ans_dict' in fault_localization_res['result_dict']:
                prompt_fl += 'The generated code has an error at %s, and the last executable part is %s, whose value is %s\n' % (
                    fault_localization_res['last_unexec_part'],
                    fault_localization_res['last_exec_part'],
                    fault_localization_res['last_exec_part_value'],
                )
            prompt_fl += '##########\n\n'

            prompt_fl += ('# Fact Checking #\n')
            prompt_fl += 'The generated code violated the logic stated in the description:\n%s\n' % (
                ds1000[pid]['prompt'].split('A:\n<code>')[0].strip())
            prompt_fl += '##########\n\n'


        exec_environment = {}
        # print(solution)
        # Execute the script within the defined scope
        exec(ds1000[pid]['code_context'], {}, exec_environment)
        exec_context = exec_environment['exec_context']
        # head = 'The generated code is incorrect.\n'
        # additional = '\n###\nPlease also focus on whether the generated code\'s intention aligned with the code problem description.\n'
        # instruction = 'Please repair the code and generate correct Python3 code that can replace [insert] in the following test suit and also store the result into \'result\' variable:\n%s\n' % (exec_context)
        prompt_fl += '# Response #\n'
        prompt_fl += 'Please repair the code and generate correct Python3 code that can replace [insert] in the following test suit:\n%s\n' % (
            exec_context)
        prompt_fl += '##########'


        if conversation:
            new_message = [
                {"role": "system", "content": 'You are a helpful programming assistant. '
                                              'You are helping a user write a program to solve a problem. '
                                              'The user has written some code, but it has some errors and is not passing the tests.'
                                              'Please use the information provided to generate the correct code.'}
            ]
            new_message.append({"role": "user", "content": prompt_fl}),

            return new_message
        else:
            return prompt_fl

    else:
        prompt_fl = ''
        if option['stderr_only']:
            prompt_fl += '###\nAvoid the generated code that has the following error:\n'
            prompt_fl += mask_the_local_info(stderr) + '\n'


        fault_localization_res = get_bug_info(pid, generated_code)

        library_name_list, special_name_list, import_lib_dic = get_library_alains(ds1000, pid)
        function_name_list = get_function_name_in_code_line(generated_code, library_name_list, special_name_list, import_lib_dic)
        function_name_list = list(set(function_name_list))
        print(library_name_list, special_name_list, import_lib_dic)
        print(function_name_list)
        # kg_classifier_flag = kg_classifier(pid, function_name_list, ds1000[pid]['metadata']['library'].lower())
        # print(kg_classifier_flag)

        # fault localization
        if fault_localization_res['test_case']:
            prompt_fl += ('###\nBelow are the detailed error information for the generated code:\n')
            prompt_fl += 'Given the example in the prompt:\n'
            prompt_fl += 'Test case:\n'
            for test_case in fault_localization_res['test_case']:
                prompt_fl += 'Input: %s\nOutput:%s\n' % (test_case['input'], test_case['output'])
            if 'ans_dict' in fault_localization_res['result_dict']:
                prompt_fl += 'The generated code has an error at %s, and the last executable part is %s, whose value is %s\n' % (
                    fault_localization_res['last_unexec_part'],
                    fault_localization_res['last_exec_part'],
                    fault_localization_res['last_exec_part_value'],
                )
            prompt_fl += 'The generated code violated the logic stated in the description:\n%s\n' % (ds1000[pid]['prompt'].split('A:\n<code>')[0].strip())

        exec_environment = {}
        # print(solution)
        # Execute the script within the defined scope
        exec(ds1000[pid]['code_context'], {}, exec_environment)
        exec_context = exec_environment['exec_context']
        head = 'The generated code is incorrect.\n'
        # additional = '\n###\nPlease also focus on whether the generated code\'s intention aligned with the code problem description.\n'
        # instruction = 'Please repair the code and generate correct Python3 code that can replace [insert] in the following test suit and also store the result into \'result\' variable:\n%s\n' % (exec_context)
        instruction = 'Please repair the code and generate correct Python3 code that can replace [insert] in the following test suit:\n%s\n' % (exec_context)

        if conversation:
            new_message = []
            new_message.append({"role": "user", "content": ds1000[pid]['prompt']})
            new_message.append({"role": "assistant", "content": generated_code}),
            new_message.append({"role": "user", "content": head + prompt_fl + '\n###\n' + instruction}),
            # new_message.append({"role": "user", "content": head + prompt_kg_fl + '\n###\n' + setting['instruction_prompt']}),
            return new_message
        else:

            return setting['instruction_prompt'] +original_prompt + '\n\n' + head + generated_code + '\n' + prompt_fl


def enrich_prompt_with_explanation(ds1000, pid, message, stderr, generated_code, original_prompt, explanation_dic, conversation=False, setting={}):
    prompt_sr = ''
    # prompt_sr = '###\nGiven the code generation task below:\n'
    # prompt_sr += ds1000[pid]['prompt'] + '\n'
    # prompt_sr += '###\nGiven the generated incorrect code below:\n'
    # prompt_sr += generated_code + '\n'
    prompt_sr += '###\nBelow is the error information:\n'
    prompt_sr += stderr + '\n'
    prompt_sr += explanation_dic[pid]

    # generate explanation

    if conversation:
        new_message = []
        new_message += message
        new_message.append({"role": "assistant", "content": generated_code+'\n</code>\nEND SOLUTION'}),
        new_message.append({"role": "user", "content": prompt_sr + '\n###\n' + setting['instruction_prompt']}),
        return new_message
    else:
        head = 'The generated code is incorrect.\n'
        return setting['instruction_prompt'] + original_prompt + '\n\n' + head + generated_code + '\n' + prompt_sr


def generate_nl(ds1000, pid, generated_code):
    # prompt_kg_fl = 'The generated code is incorrect.\n'
    # prompt_kg_fl = ''

    # prompt_kg_fl += 'Below is the information that could help to generate a correct code:\n'
    fault_localization_res = get_bug_info(pid, generated_code)


    library_name_list, special_name_list = get_library_alains(ds1000, pid)
    function_name_list = get_function_name_in_code_line(generated_code, library_name_list, special_name_list)
    function_name_list = list(set(function_name_list))


    classifier_flag_dic = {}
    tmp_nl = ''
    if not classifier_flag_dic:
        error_function_triplet_dic = load_kg_info(function_name_list, ds1000, pid)

        query_result_list = []
        if error_function_triplet_dic:
            for error_function_name in error_function_triplet_dic:
                # html_triplets += error_res['error_function_triplet_dic'][error_function_name]['html_triplets']
                query_result_list.append(error_function_triplet_dic[error_function_name]['html_triplets'])
        tmp_nl = query_result_list2natural_language(query_result_list)

    else:
        if classifier_flag_dic[pid]:
            error_function_triplet_dic = load_kg_info(function_name_list, ds1000, pid)

            query_result_list = []
            if error_function_triplet_dic:
                for error_function_name in error_function_triplet_dic:
                    # html_triplets += error_res['error_function_triplet_dic'][error_function_name]['html_triplets']
                    query_result_list.append(error_function_triplet_dic[error_function_name]['html_triplets'])
            tmp_nl = query_result_list2natural_language(query_result_list)

    prompt_fl = ''
    # fault localization
    if fault_localization_res['test_case']:
        prompt_fl += ('###\nBelow are the detailed error information for the generated code:\n')
        prompt_fl += 'Given the example in the prompt:\n'
        prompt_fl += 'Test case:\n'
        for test_case in fault_localization_res['test_case']:
            prompt_fl += 'Input: %s\nOutput:%s\n' % (test_case['input'], test_case['output'])
        if 'ans_dict' in fault_localization_res['result_dict']:
            prompt_fl += 'The generated code has an error at %s, and the last executable part is %s, whose value is %s\n' % (
                fault_localization_res['last_unexec_part'],
                fault_localization_res['last_exec_part'],
                fault_localization_res['last_exec_part_value'],
            )
    return tmp_nl, prompt_fl


def enrich_test_res_list(test_res_list, ds1000):
    for i, test_res in enumerate(test_res_list):
        kg_nl, fl_nl = generate_nl(ds1000, test_res['pid'], test_res['generated_code'])
        test_res_list[i]['kg_nl'] = kg_nl
        test_res_list[i]['fl_nl'] = fl_nl
    return test_res_list


def enrich_prompt_with_simple_feedback(message, generated_code, original_prompt, conversation=False, setting={}):
    prompt_sf = ''

    prompt_sf += 'The generated code is incorrect. Please fix the code.\n'
    if conversation:
        new_message = []
        new_message += message
        new_message.append({"role": "assistant", "content": generated_code+'\n</code>\nEND SOLUTION'}),
        new_message.append({"role": "user", "content": prompt_sf + '\n###\n' + setting['instruction_prompt']}),
        return new_message
    else:
        return setting['instruction_prompt'] + original_prompt + '\n\n' + generated_code + '\n' + prompt_sf


def enrich_prompt_with_trace(message, stderr, original_prompt, generated_code, setting, conversation=False):
    prompt = '###\nAvoid the generated code that has the following error:\n'
    prompt += mask_the_local_info(stderr) + '\n'
    prompt += 'Using the provided informarion, trace through the execution of the code to determine what needs to be fixed, and correct the code.'

    if conversation:
        new_message = []
        new_message += message
        new_message.append({"role": "assistant", "content": generated_code +'\n</code>\nEND SOLUTION'}),
        new_message.append({"role": "user", "content": prompt+ '\n###\n' + setting['instruction_prompt']}),
        return new_message
    else:
        return prompt + '\n' + original_prompt


def enrich_prompt_for_error_code(test_res_list, ds1000, repair_index, search_res_dic={}, option=None, setting={}):
    # default
    if not option:
        code_search = False
        baseline = False
        triplet_only = True
        stderr_first = True
        stderr_only = False
        conversation = False
        natural_language = False
        with_bug_code = False
        fault_localization = False
        kg = False
        classifier = False
    else:
        code_search = option['code_search']
        baseline = option['baseline']
        triplet_only = option['triplet_only']
        stderr_first = option['stderr_first']
        stderr_only = option['stderr_only']
        conversation = option['conversation']
        natural_language = option['natural_language']
        with_bug_code = option['with_bug_code']
        fault_localization = option['fault_localization']
        kg = option['kg']
        classifier = option['classifier']

    if 'explanation' in option:
        if fault_localization and kg:
            test_res_list = enrich_test_res_list(test_res_list, ds1000)

        explanation_dic = generate_explanation_for_repair(test_res_list, ds1000, repair_index, option['model'])
        id_prompt_list = []
        for test_res in test_res_list:
            enriched_prompt = enrich_prompt_with_explanation(ds1000, test_res['pid'], test_res['message'], test_res['stderr'],
                                          test_res['generated_code'],
                                          ds1000[test_res['pid']]['prompt'],
                                          explanation_dic,
                                          conversation=conversation,
                                          setting=setting)
            id_prompt_list.append([test_res['pid'], enriched_prompt])
        return id_prompt_list

    if 'simple_feedback' in option:
        id_prompt_list = []
        for test_res in test_res_list:
            enriched_prompt = enrich_prompt_with_simple_feedback(test_res['message'], test_res['generated_code'],
                                                                 ds1000[test_res['pid']]['prompt'],
                                                                 conversation=conversation, setting=setting)
            id_prompt_list.append([test_res['pid'], enriched_prompt])
        return id_prompt_list

    if 'line_explanation' in option:
        explanation_dic = generate_line_explanation_for_repair(test_res_list, ds1000, repair_index)
        id_prompt_list = []
        for test_res in test_res_list:
            enriched_prompt = enrich_prompt_with_explanation(ds1000, test_res['pid'], test_res['message'], test_res['stderr'],
                                          test_res['generated_code'],
                                          ds1000[test_res['pid']]['prompt'],
                                          explanation_dic,
                                          conversation=conversation,
                                          setting=setting)
            id_prompt_list.append([test_res['pid'], enriched_prompt])
        return id_prompt_list

    if 'trace' in option:
        id_prompt_list = []
        for test_res in test_res_list:
            enriched_prompt = enrich_prompt_with_trace(test_res['message'], test_res['stderr'],
                                                        ds1000[test_res['pid']]['prompt'], test_res['generated_code'],
                                                        setting=setting,
                                                        conversation=conversation)
            id_prompt_list.append([test_res['pid'], enriched_prompt])
        return id_prompt_list



    if fault_localization:
        total = 0
        if kg:
            # if classifier:
            #     print('Using classifier...')
            #     classifier_dic = get_kg_classifier_dic(test_res_list, ds1000, repair_index, 'direct_classifier')
            # else:
            #     classifier_dic = {}
            plain_text_dic = {}
            if 'plain_text' in option:
                with open('knowledge_graph/plain_text.json', 'r') as f:
                    original_plain_text_dic = json.load(f)
                for key in original_plain_text_dic:
                    plain_text_dic[key] = nltk_tokenize(original_plain_text_dic[key])

            id_prompt_list = []
            for test_res in test_res_list:
                enriched_prompt, demo = enrich_prompt_with_kg_fault_localization(ds1000, test_res['pid'], test_res['message'],
                                                                           test_res['stderr'],
                                                                           test_res['generated_code'],
                                                                           ds1000[test_res['pid']]['prompt'],
                                                                           option,
                                                                           plain_text_dic=plain_text_dic,
                                                                           conversation=conversation,
                                                                           setting=setting)
                id_prompt_list.append([test_res['pid'], enriched_prompt])
                total += demo
            print(total)
            return id_prompt_list
        else:
            id_prompt_list = []
            for test_res in test_res_list:
                enriched_prompt = enrich_prompt_with_fault_localization(ds1000, test_res['pid'], test_res['message'],
                                                                        test_res['stderr'],
                                                                        test_res['generated_code'],
                                                                        ds1000[test_res['pid']]['prompt'],
                                                                        option=option,
                                                                        conversation=conversation,
                                                                        setting=setting)
                id_prompt_list.append([test_res['pid'], enriched_prompt])
            return id_prompt_list

    if code_search:
        if stderr_only:
            id_prompt_list = []
            for test_res in test_res_list:
                enriched_prompt = enrich_prompt_with_stderr_search_result(test_res['pid'], test_res['message'],
                                                                          test_res['stderr'], test_res['generated_code'],
                                                                          search_res_dic,
                                                                          ds1000[test_res['pid']]['prompt'],
                                                                          option=option,
                                                                          conversation=conversation,
                                                                          setting=setting
                                                                          )
                id_prompt_list.append([test_res['pid'], enriched_prompt])
            return id_prompt_list
        else:
            id_prompt_list = []
            for test_res in test_res_list:
                enriched_prompt = enrich_prompt_with_search_result(test_res['pid'], test_res['message'],
                                                                          test_res['generated_code'],
                                                                          search_res_dic,
                                                                          ds1000[test_res['pid']]['prompt'],
                                                                          option=option,
                                                                          conversation=conversation,
                                                                          setting=setting
                                                                          )
                id_prompt_list.append([test_res['pid'], enriched_prompt])
            return id_prompt_list


    if baseline:
        # use the original prompt
        id_prompt_list = []
        for test_res in test_res_list:
            id_prompt_list.append([test_res['pid'], ds1000[test_res['pid']]['prompt']])
        return id_prompt_list
    if stderr_only:
        # similar to chatrepair (but for 1-shot)
        id_prompt_list = []
        for test_res in test_res_list:
            # std_err_list = [x['stderr'] for x in error_res['process_info_list'] if x['return_code']!=0]
            # std_err_list = list(set(std_err_list))
            # enriched_prompt = enrich_prompt_with_stderr(std_err_list, error_res['prompt'], error_res['generated_code'],
            enriched_prompt = enrich_prompt_with_stderr(test_res['message'], test_res['stderr'],
                                                        ds1000[test_res['pid']]['prompt'], test_res['generated_code'],
                                                        setting=setting,
                                                        conversation=conversation,
                                                        natural_language=natural_language,
                                                        with_bug_code=with_bug_code)
            id_prompt_list.append([test_res['pid'], enriched_prompt])
        return id_prompt_list


    print('Loading triplets...')
    # with open('tmp_triplets_test_res_list.json1', 'w') as f:
    #     f.write(json.dumps(test_res_list))
    # with open('tmp_triplets_test_res_list.json1', 'r') as f:
    #     test_res_list = json.load(f)
    test_res_list = load_triplets_new(test_res_list, ds1000)
    print('Done loading triplets!')

    # put triplets into the prompt
    new_list = []
    for error_res in test_res_list:
        query_result_list = []
        if 'error_function_triplet_dic' in error_res:
            for error_function_name in error_res['error_function_triplet_dic']:
                # html_triplets += error_res['error_function_triplet_dic'][error_function_name]['html_triplets']
                query_result_list.append(error_res['error_function_triplet_dic'][error_function_name]['html_triplets'])
        if triplet_only:
            enriched_prompt_html = enrich_prompt_with_triplets(query_result_list, ds1000[error_res['pid']]['prompt'],
                                                               conversation=conversation,
                                                               natural_language=natural_language)
        else:
            enriched_prompt_html = enrich_prompt_with_stderr_and_triplets(query_result_list, error_res['message'],
                                                                          error_res['stderr'],
                                                                          ds1000[error_res['pid']]['prompt'],
                                                                          error_res['generated_code'],
                                                                          conversation=conversation,
                                                                          stderr_first=stderr_first,
                                                                          natural_language=natural_language,
                                                                          with_bug_code=with_bug_code,
                                                                          setting=setting)
        new_list.append({
            'enriched_prompt_html': enriched_prompt_html,
            'id': error_res['pid']
        })
    id_prompt_list_html = [[dic['id'], dic['enriched_prompt_html']] for dic in new_list]

    return id_prompt_list_html


def load_triplets(test_res_list, ds1000, html_kg_toolkit_dic):
    error_res_dic_list = []
    # query the kg_repair
    for res in test_res_list:
        print(res['pid'])
        # res = run_test_res_dic_list[8]
        html_kg_toolkit = html_kg_toolkit_dic[ds1000[res['pid']]['metadata']['library'].lower()+'_html_kg_toolkit']
        query_result_html = []
        error_function_triplet_dic = {}
        # for x in res['process_info_list']:
        #     if x['stderr']:
        # error_info_dic = res['error_info_dic']
        # error_res_dic_list.append(res)
        error_function_name_list = error_code_line_analyze(res, ds1000)

        if error_function_name_list:
            for error_function_name in error_function_name_list:
                query = build_SPARQL_query(error_function_name, ds1000[res['pid']]['metadata']['library'].lower())
                query_result_html = html_kg_toolkit.query_KG(query)

                # parameter_pid_list_code = []
                parameter_pid_list_html = []
                # return_pid_list_code = []
                return_pid_list_html = []
                # for triplet in query_result_code:
                #     if re.search(r'parameter_\d+$', triplet[2]):
                #         parameter_pid_list_code.append(triplet[2])
                #     elif re.search(r'return_\d+$', triplet[2]):
                #         return_pid_list_code.append(triplet[2])
                for triplet in query_result_html:
                    if re.search(r'parameter_\d+$', triplet[2]):
                        parameter_pid_list_html.append(triplet[2])
                    elif re.search(r'return_\d+$', triplet[2]):
                        return_pid_list_html.append(triplet[2])

                # parameter_pid_list_code = list(set(parameter_pid_list_code))
                parameter_pid_list_html = list(set(parameter_pid_list_html))
                # return_pid_list_code = list(set(return_pid_list_code))
                return_pid_list_html = list(set(return_pid_list_html))

                # second_query_result_code = code_kg_toolkit.do_second_query(
                #     parameter_pid_list_code,
                #     return_pid_list_code,
                #     False)
                second_query_result_html = html_kg_toolkit.do_second_query(
                    parameter_pid_list_html,
                    return_pid_list_html,
                    False)

                # query_result_code += (second_query_result_code[0] + second_query_result_code[1])
                query_result_html += (second_query_result_html[0] + second_query_result_html[1])

                if error_function_name not in error_function_triplet_dic:
                    error_function_triplet_dic[error_function_name] = {
                        # 'code_triplets': query_result_code,
                        'html_triplets': query_result_html
                    }
                else:
                    # error_function_triplet_dic[error_function_name][
                    #     'code_triplets'] += query_result_code
                    error_function_triplet_dic[error_function_name][
                        'html_triplets'] += query_result_html
        if error_function_triplet_dic:
            for key in error_function_triplet_dic:
                # error_function_triplet_dic[key]['code_triplets'] = list(
                #     set(error_function_triplet_dic[key]['code_triplets']))
                error_function_triplet_dic[key]['html_triplets'] = list(
                    set(error_function_triplet_dic[key]['html_triplets']))
            res['error_function_triplet_dic'] = error_function_triplet_dic
        error_res_dic_list.append(res)
    return error_res_dic_list


def load_triplets_new(test_res_list, ds1000, enable_blur_query=False):
    api = kg_api.KgAPI()
    error_res_dic_list = []
    # query the kg_repair
    for res in test_res_list:
        print(res['pid'])
        error_function_triplet_dic = {}
        error_function_name_list = list(set(error_code_line_analyze(res, ds1000)))
        if error_function_name_list:
            for error_function_name in error_function_name_list:

                exact_query = build_SPARQL_query_exact(error_function_name, ds1000[res['pid']]['metadata']['library'].lower())
                print('Exact query...')
                query_result = api.query_knowledge_graph(exact_query).convert()
                query_result['query_type'] = 'exact_query'
                if query_result['results']['bindings']:
                    # if error_function_name not in error_function_triplet_dic:
                    error_function_triplet_dic[error_function_name] = {
                        'html_triplets': query_result
                    }
                else:
                    if enable_blur_query:
                        blur_query = build_SPARQL_query_blur(error_function_name,
                                                               ds1000[res['pid']]['metadata']['library'].lower())
                        print('Blur query...')
                        query_result = api.query_knowledge_graph(blur_query).convert()
                        query_result['query_type'] = 'blur_query'

                        error_function_triplet_dic[error_function_name] = {
                            'html_triplets': query_result
                        }
                    else:
                        error_function_triplet_dic[error_function_name] = {
                            'html_triplets': query_result
                        }
            res['error_function_triplet_dic'] = error_function_triplet_dic
        else:
            print('No functions detected in the error line.')
        error_res_dic_list.append(res)
    return error_res_dic_list

def load_kg_info(error_function_name_list, ds1000, pid, enable_blur_query=False):
    api = kg_api.KgAPI()
    error_function_triplet_dic = {}
    if error_function_name_list:
        for error_function_name in error_function_name_list:

            exact_query = build_SPARQL_query_exact(error_function_name,
                                                   ds1000[pid]['metadata']['library'].lower())
            print('Exact query...')
            if api.query_knowledge_graph(exact_query):
                query_result = api.query_knowledge_graph(exact_query).convert()
            else:
                continue
            query_result['query_type'] = 'exact_query'
            if query_result['results']['bindings']:
                # if error_function_name not in error_function_triplet_dic:
                error_function_triplet_dic[error_function_name] = {
                    'html_triplets': query_result
                }
            else:
                if enable_blur_query:
                    blur_query = build_SPARQL_query_blur(error_function_name,
                                                         ds1000[pid]['metadata']['library'].lower())
                    print('Blur query...')
                    query_result = api.query_knowledge_graph(blur_query).convert()
                    query_result['query_type'] = 'blur_query'

                    error_function_triplet_dic[error_function_name] = {
                        'html_triplets': query_result
                    }
                else:
                    error_function_triplet_dic[error_function_name] = {
                        'html_triplets': query_result
                    }
    else:
        print('No functions detected in the error line.')

    return error_function_triplet_dic

def triplet_simplify(triplet, namespace):
    new_triplet = []
    for x in triplet:
        new_triplet.append(x.replace(namespace, ''))
    return new_triplet

def triplet_list2natural_language(triplet_list, namespace):
    res_nl = ''
    enriched_prompt_dic = triplet_list2dic(triplet_list, namespace)
    # pprint(enriched_prompt_dic)
    # is_a
    if 'is_a' in enriched_prompt_dic:
        res_nl += enriched_prompt_dic['is_a'] + '\n'
    # full expression
    if 'object_expression' in enriched_prompt_dic:
        res_nl += enriched_prompt_dic['object_expression'] + '\n'
    # explanation
    if 'explanation' in enriched_prompt_dic:
        res_nl += enriched_prompt_dic['explanation'] + '\n'
    # parameter
    if 'parameter' in enriched_prompt_dic:
        res_nl += enriched_prompt_dic['parameter'] + ' '
        parameter_no = 0
        while str(parameter_no) in enriched_prompt_dic['parameter_dic']:
            item = enriched_prompt_dic['parameter_dic'][str(parameter_no)]
            res_nl += item['explanation'] + ' '
            try:
                res_nl += 'The type of parameter \'%s\' is %s.' % (item['name'], item['type']) + '\n'
            except:
                pass
            parameter_no += 1
    # return
    if 'return' in enriched_prompt_dic:
        res_nl += enriched_prompt_dic['return'] + ' '
        return_no = 0
        while str(return_no) in enriched_prompt_dic['return_dic']:
            item = enriched_prompt_dic['return_dic'][str(return_no)]
            res_nl += item['explanation'] + ' '
            res_nl += 'The type of return \'%s\' is %s.' % (item['name'], item['type'])  + '\n'
            return_no += 1

    if 'note' in enriched_prompt_dic:
        res_nl += enriched_prompt_dic['note']
    # example
    if 'example' in enriched_prompt_dic:
        res_nl += enriched_prompt_dic['example']
    return res_nl


def triplet_list2dic(triplet_list, namespace):
    enriched_prompt_dic = {}
    parameter_triplet_list = []
    return_triplet_list = []
    for triplet in triplet_list:
        triplet = triplet_simplify(triplet, namespace)
        object = triplet[0].split('/')[-1]
        if re.search(r'parameter_\d+$', triplet[0]):
            parameter_triplet_list.append(triplet)
        elif re.search(r'return_\d+$', triplet[0]):
            return_triplet_list.append(triplet)
        else:
            if triplet[1].endswith('has_explanation'):
                if triplet[2]:
                    enriched_prompt_dic['explanation'] = '%s' % (triplet[2])
            elif triplet[1].endswith('has_object_expression'):
                if triplet[2]:
                    enriched_prompt_dic['object_expression'] = 'The full expression of \'%s\' is %s.' % (object, triplet[2])
            elif triplet[1].endswith('is_a'):
                if triplet[2]:
                    enriched_prompt_dic['is_a'] = '\'%s\' is a %s.' % (object, triplet[2].replace('py', 'python'))
            elif triplet[1].endswith('has_parameter'):
                pass
            elif triplet[1].endswith('has_return'):
                pass
            elif triplet[1].endswith('has_example'):
                if 'example' not in enriched_prompt_dic:
                    enriched_prompt_dic['example'] = 'Below is an example of the usage of \'%s\':\n%s' % (
                        object, triplet[2])
                else:
                    enriched_prompt_dic['example'] += '\n' + triplet[2]
            elif triplet[1].endswith('has_note'):
                if triplet[2]:
                    enriched_prompt_dic['note'] = triplet[2]
            elif 'has_py' in triplet[1]:
                pass

    # print(parameter_triplet_list)

    if parameter_triplet_list:
        parameter_no = len(list(set([x[0] for x in parameter_triplet_list])))
        object = parameter_triplet_list[0][0].split('/')[0]
        if parameter_no > 1:
            enriched_prompt_dic['parameter'] = 'There are %s parameters in \'%s\'.' % (parameter_no, object)
        else:
            enriched_prompt_dic['parameter'] = 'There is %s parameter in \'%s\'.' % (parameter_no, object)


    if return_triplet_list:
        return_no = len(list(set([x[0] for x in return_triplet_list])))
        object = return_triplet_list[0][0].split('/')[0]
        if return_no > 1:
            enriched_prompt_dic['return'] = 'There are %s elements returned in \'%s\'.' % (return_no, object)
        else:
            enriched_prompt_dic['return'] = 'There is %s element returned in \'%s\'.' % (return_no, object)


    # parameter info
    enriched_prompt_dic['parameter_dic'] = {}
    for triplet in parameter_triplet_list:
        if triplet[0][-1] not in enriched_prompt_dic['parameter_dic']:
            enriched_prompt_dic['parameter_dic'][triplet[0][-1]] = {}
        if 'has_name' in triplet[1]:
            enriched_prompt_dic['parameter_dic'][triplet[0][-1]]['name'] = triplet[2]
        elif 'has_type' in triplet[1]:
            enriched_prompt_dic['parameter_dic'][triplet[0][-1]]['type'] = triplet[2]
        elif 'has_explanation' in triplet[1]:
            enriched_prompt_dic['parameter_dic'][triplet[0][-1]]['explanation'] = triplet[2]

    enriched_prompt_dic['return_dic'] = {}
    for triplet in return_triplet_list:
        if triplet[0][-1] not in enriched_prompt_dic['return_dic']:
            enriched_prompt_dic['return_dic'][triplet[0][-1]] = {}
        if 'has_name' in triplet[1]:
            enriched_prompt_dic['return_dic'][triplet[0][-1]]['name'] = triplet[2]
        elif 'has_type' in triplet[1]:
            enriched_prompt_dic['return_dic'][triplet[0][-1]]['type'] = triplet[2]
        elif 'has_explanation' in triplet[1]:
            enriched_prompt_dic['return_dic'][triplet[0][-1]]['explanation'] = triplet[2]

    return enriched_prompt_dic


def query_result2dic(query_result_list):
    def _remove_prefix(text):
        rdf_prefix = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        kg4cg_prefix = 'http://w3id.org/kg4cg/vocab#'
        return text.replace(rdf_prefix, '').replace(kg4cg_prefix, '')

    tmp_res_dic_list = []
    for query_result in query_result_list:
        tmp_res_dic = {}
        for triplet_dic in query_result['results']['bindings']:
            # len(key) = 3
            if len(triplet_dic.keys()) == 3:
                if _remove_prefix(triplet_dic['predicate']['value']) == 'type':
                    tmp_res_dic['object_type'] = _remove_prefix(triplet_dic['object']['value'])
                elif _remove_prefix(triplet_dic['predicate']['value']) == 'hasName':
                    tmp_res_dic['name'] = _remove_prefix(triplet_dic['object']['value'])
                elif _remove_prefix(triplet_dic['predicate']['value']) == 'belongsToLibrary':
                    tmp_res_dic['library'] = _remove_prefix(triplet_dic['object']['value'])
                elif _remove_prefix(triplet_dic['predicate']['value']) == 'belongsToModule':
                    # can be empty
                    if _remove_prefix(triplet_dic['object']['value']):
                        tmp_res_dic['module'] = _remove_prefix(triplet_dic['object']['value'])
                elif _remove_prefix(triplet_dic['predicate']['value']) == 'hasExplanation':
                    tmp_res_dic['explanation'] = _remove_prefix(triplet_dic['object']['value'])
                elif _remove_prefix(triplet_dic['predicate']['value']) == 'hasExpression':
                    tmp_res_dic['full_expression'] = _remove_prefix(triplet_dic['object']['value'])
                elif _remove_prefix(triplet_dic['predicate']['value']) == 'hasNote':
                    tmp_res_dic['note'] = _remove_prefix(triplet_dic['object']['value'])
            elif len(triplet_dic.keys()) == 5:
                if _remove_prefix(triplet_dic['predicate']['value']) == 'hasParameter':
                    if 'Parameter' not in tmp_res_dic:
                        tmp_res_dic['Parameter'] = {}
                    key = _remove_prefix(triplet_dic['object']['value'])
                    if key not in tmp_res_dic['Parameter']:
                        tmp_res_dic['Parameter'][key] = {}

                    if _remove_prefix(triplet_dic['predicate1']['value']) == 'type':
                        tmp_res_dic['Parameter'][key]['object_type'] = _remove_prefix(triplet_dic['object1']['value'])
                    elif _remove_prefix(triplet_dic['predicate1']['value']) == 'hasName':
                        tmp_res_dic['Parameter'][key]['name'] = _remove_prefix(triplet_dic['object1']['value'])
                    elif _remove_prefix(triplet_dic['predicate1']['value']) == 'hasExplanation':
                        tmp_res_dic['Parameter'][key]['explanation'] = _remove_prefix(triplet_dic['object1']['value'])
                    elif _remove_prefix(triplet_dic['predicate1']['value']) == 'hasType':
                        tmp_res_dic['Parameter'][key]['type'] = _remove_prefix(triplet_dic['object1']['value'])
                    elif _remove_prefix(triplet_dic['predicate1']['value']) == 'hasPid':
                        tmp_res_dic['Parameter'][key]['pid'] = _remove_prefix(triplet_dic['object1']['value'])

                elif _remove_prefix(triplet_dic['predicate']['value']) == 'hasReturn':
                    if 'Return' not in tmp_res_dic:
                        tmp_res_dic['Return'] = {}
                    key = _remove_prefix(triplet_dic['object']['value'])
                    if key not in tmp_res_dic['Return']:
                        tmp_res_dic['Return'][key] = {}
                    if _remove_prefix(triplet_dic['predicate1']['value']) == 'type':
                        tmp_res_dic['Return'][key]['object_type'] = _remove_prefix(triplet_dic['object1']['value'])
                    elif _remove_prefix(triplet_dic['predicate1']['value']) == 'hasName':
                        tmp_res_dic['Return'][key]['name'] = _remove_prefix(triplet_dic['object1']['value'])
                    elif _remove_prefix(triplet_dic['predicate1']['value']) == 'hasExplanation':
                        tmp_res_dic['Return'][key]['explanation'] = _remove_prefix(triplet_dic['object1']['value'])
                    elif _remove_prefix(triplet_dic['predicate1']['value']) == 'hasType':
                        tmp_res_dic['Return'][key]['type'] = _remove_prefix(triplet_dic['object1']['value'])
                    elif _remove_prefix(triplet_dic['predicate1']['value']) == 'hasPid':
                        tmp_res_dic['Return'][key]['pid'] = _remove_prefix(triplet_dic['object1']['value'])
        tmp_res_dic_list.append(tmp_res_dic)
    return tmp_res_dic_list

def enriched_prompt_dic2nl(enriched_prompt_dic):
    # print(enriched_prompt_dic)
    res_nl = ''
    # try:
    # reduce length
    if 'full_expression' in enriched_prompt_dic:
        res_nl += enriched_prompt_dic['full_expression'] + '\n'
        # res_nl += '%s has full expression %s\n' % (enriched_prompt_dic['name'], enriched_prompt_dic['full_expression'])
        # res_nl += 'please check the setting of the optional paramaters in its expression.\n'
    if 'explanation' in enriched_prompt_dic:
        res_nl += '%s\n' % (enriched_prompt_dic['explanation'])
    # if 'note' in enriched_prompt_dic:
    #     res_nl += '%s\n' % (enriched_prompt_dic['note'])

    if 'Parameter' in enriched_prompt_dic:
        if len(enriched_prompt_dic['Parameter']) > 1:
            res_nl += '%s has %s parameters.\n' % (enriched_prompt_dic['name'], len(enriched_prompt_dic['Parameter']))
        else:
            res_nl += '%s has %s parameter.\n' % (enriched_prompt_dic['name'], len(enriched_prompt_dic['Parameter']))
        parameter_nl_list = []
        for parameter_key in enriched_prompt_dic['Parameter']:
            parameter_nl = ''
            if 'type' in enriched_prompt_dic['Parameter'][parameter_key]:
                parameter_nl += '%s is %s\n' % (enriched_prompt_dic['Parameter'][parameter_key]['name'],
                                                enriched_prompt_dic['Parameter'][parameter_key]['type'])
            if 'explanation' in enriched_prompt_dic['Parameter'][parameter_key]:
                parameter_nl += '%s\n' % (enriched_prompt_dic['Parameter'][parameter_key]['explanation'])
            parameter_nl_list.append((int(enriched_prompt_dic['Parameter'][parameter_key]['pid']), parameter_nl))

        parameter_nl_list = sorted(parameter_nl_list, key=lambda x: x[0])
        res_nl += '\n'.join([x[1] for x in parameter_nl_list])

    if 'Return' in enriched_prompt_dic:
        if len(enriched_prompt_dic['Return']) > 1:
            res_nl += '%s has %s returns.' % (enriched_prompt_dic['name'], len(enriched_prompt_dic['Return']))
        else:
            res_nl += '%s has %s return.' % (enriched_prompt_dic['name'], len(enriched_prompt_dic['Return']))
        return_nl_list = []
        for return_key in enriched_prompt_dic['Return']:
            return_nl = ''
            if 'type' in enriched_prompt_dic['Return'][return_key]:
                return_nl += '%s is %s\n' % (enriched_prompt_dic['Return'][return_key]['name'],
                                             enriched_prompt_dic['Return'][return_key]['type'])
            if 'explanation' in enriched_prompt_dic['Return'][return_key]:
                return_nl += '%s\n' % (enriched_prompt_dic['Return'][return_key]['explanation'])
            return_nl_list.append((int(enriched_prompt_dic['Return'][return_key]['pid']), return_nl))

        return_nl_list = sorted(return_nl_list, key=lambda x: x[0])  # ascend
        res_nl += '\n'.join([x[1] for x in return_nl_list])

    return res_nl


def query_result_list2natural_language(query_result_list):
    res_nl = ''
    enriched_prompt_dic_list = query_result2dic(query_result_list)
    for enriched_prompt_dic in enriched_prompt_dic_list:
        tmp = enriched_prompt_dic2nl(enriched_prompt_dic).strip()
        if tmp:
            res_nl += tmp + '\n'
    return res_nl


def chain_of_thought_prompt(stderr=False):
    if stderr:
        'The generated code has following error'
    pass


def clean_tensorflow_warnning(stderr):
    stderr_list = stderr.split('\n')


def nltk_tokenize(text):
    return word_tokenize(text)


def search_context_based_on_keyword(keyword, plain_text, library, context_length=75):
    tokens = plain_text
    results = []
    if library not in keyword:
        keyword_positions = [i for i, token in enumerate(tokens) if
                             keyword in token and library in token]
    else:
        keyword_positions = [i for i, token in enumerate(tokens) if keyword in token]

    for pos in keyword_positions:
        context_start = pos
        context_end = min(pos + context_length + 1, len(tokens))
        context = " ".join(tokens[context_start:context_end])
        results.append(context)
    return results