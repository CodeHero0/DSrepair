import json
import asyncgpt
import aiofiles
import asyncio
import re
import os
import gzip
from util import *

async def openai_model(ds1000, setting={}):
    # first code generation
    with open('openai_info/gpt_info.json', 'r') as f:
        info_dic = json.load(f)

    bot = asyncgpt.AsyncGPT(api_key=info_dic['api_key'], organization=info_dic['organization'], model=setting['model'])
    prompt_list = [generate_code(p, id, bot, setting) for id, p in enumerate(ds1000)]
    res_list = await asyncio.gather(*prompt_list)
    return res_list

async def generate_code(problem, index, bot, setting):
    if 'temperature' in setting:
        temperature = setting['temperature']
    else:
        temperature = 0

    final_prompt = setting['instruction_prompt'] + problem['prompt']
    message = [{"role": "user", "content": final_prompt}]
    completion = await bot.chat_complete(message, temperature=temperature)
    res = {'index': index,
           'metadata': problem['metadata'],
           'temperature': temperature,
           'prompt': final_prompt,
           'completion': completion,
           'message': message,
           'response': completion['choices'][0]['message']['content']
           }
    return res


def initial_code_generation(ds1000, stored_file_name, setting={}, stored_folder_path='intermediate_result/'):
    res_list = asyncio.run(openai_model(ds1000, setting))
    with open(stored_folder_path + stored_file_name + '.json', 'w') as f:
        f.write(json.dumps(res_list))


if __name__ == "__main__":
    ds1000 = [json.loads(l) for l in gzip.open("dataset/ds1000.jsonl.gz", "rt").readlines()]

    setting = {
        'model': 'gpt-3.5-turbo', # gpt-3.5-turbo-0125
        'instruction_prompt': 'Generate Python3 code ended with \'</code>\\nEND SOLUTION\'\n',
        'temperature': 0,
    }
    initial_code_generation(ds1000,
                            'ds1000_t_%s' % setting['temperature'],
                            setting=setting,
                            stored_folder_path='intermediate_result/initial_code/')