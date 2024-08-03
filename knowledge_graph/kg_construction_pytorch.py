import os
from bs4 import BeautifulSoup
import re
from rdflib import Graph, Namespace, Literal, URIRef
import lxml
from kg_construction_tookit import (get_object_type_new, relation_analyze, remove_prefix,
                                    transfer_element_dic_2_triplet, entailment_relationship2triplet, object_name_clean,
                                    transfer_element_dic_2_triplet_new)
from pprint import pprint
import sys
# sys.path
sys.path.append('../')
import kg_api


# pytorch version: 2.2.0

def get_dic(tag_list, parameter_dic, is_return=False):
    parameter_list = []
    parameter_id = 0
    # print(tag_list)
    for i, x in enumerate(tag_list):
        if x.text.strip():
            tmp = []
            for child in x.children:
                # print(child.name, child)
                if child.text.strip():
                    if '<strong>' in str(child):
                        if hasattr(child.strong, 'text'):
                            # print(child)
                            tmp.append('parameter:' + child.strong.text)
                        else:
                            tmp.append('parameter:' + child.text)
                        tmp.append('pid:' + str(parameter_id))
                        parameter_id += 1
                        if '(' in str(child) and ')' in str(child):
                            # print('aaaaa', child.text)
                            match = re.search(r'\((.*?)\)', child.text.strip())

                            tmp.append('type:' + match.group(1))
                    if child.name == 'p':
                        if '–' in str(child):
                            tmp.append(child.text.split('–', 1)[1].strip())
                        else:
                            tmp.append(child.text.strip())
                    else:
                        if child.name != 'strong':
                            if '–' in str(child):
                                tmp.append(child.text.split('–', 1)[1].strip())
                            else:
                                tmp.append(child.text.strip())

            parameter_list.append(tmp)
    # print(parameter_list)

    # parameter_dic = {}
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

def get_element_from_html(html_file):
    # html_file = 'KG_source/pytorch-html/generated/torch.nn.Module.html'
    # html_file = 'KG_source/pytorch-html/generated/torch.fft.hfft.html'
    # html_file = 'KG_source/pytorch-html/generated/torch.fft.fft2.html'
    with open(html_file, encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'lxml')

    # get the article
    article_element = soup.find('article', class_='pytorch-article')
    if not article_element:
        print('page not available!')
        # return None, None
    soup_object_list = get_object_type_new(article_element)
    entailment_relationships = []
    if len(soup_object_list) >= 1:
        entailment_relationships = relation_analyze(soup_object_list)

    # for the first object, the rest objects need to add suffix
    object_name_prefix = article_element.h1.text.strip()
    object_name_prefix = object_name_clean(object_name_prefix)
    element_dic_list = []

    for index, soup_object in enumerate(soup_object_list):
        element_dic = {}
        # object type
        object_type = ' '.join(soup_object.get('class'))
        object_name = soup_object.dt.get('id')
        # object name
        if not object_name:
            if index in [x[1] for x in entailment_relationships]:
                # only need the name without parameters
                suffix_name = ''
                if soup_object.dt.find(class_='sig-name descname'):
                    tmp = soup_object.dt.find(class_='sig-name descname').text
                    # if object_type.split(' ')[-1] in tmp:
                    #     tmp = tmp.replace(object_type.split()[-1], '').strip()
                    suffix_name += '.' + tmp
                object_name = (object_name_prefix + suffix_name).strip()
            else:
                object_name = object_name_prefix.strip()
        # modified_flag = True
        object_name = object_name_clean(object_name)
        # print(object_name, object_type)


        # object full expression
        object = soup_object.find(class_='sig sig-object py').text.strip()
        if object_type.split(' ')[-1] in object:
            object = object.replace(object_type.split()[-1], '').strip()
        object = object_name_clean(object)
        # print(object)

        # object explanation
        object_explanation = ''
        # try:
        explanation_list = soup_object.dd.find_all('p', recursive=False)
        # print(explanation_list)
        for explanation in explanation_list:

            try:
                content = explanation.text.replace('\n', ' ').strip()
                if content.startswith('See also') or \
                        content.startswith('Notes') or \
                        content.startswith('Example') or \
                        content.startswith('References') or \
                        'Methods' in content:
                    break
                object_explanation += content + '\n'
            except:
                pass
        object_explanation = object_explanation.strip()
        # print(object_explanation)

        parameter_dic = {}
        attribute_dic = {}
        return_dic = {}
        exception_dic = {}
        # TODO: modify the following logic
        try:
            tmp_name = soup_object.dd.find(class_=re.compile(r'field-list')).find_all(class_='field-odd')[0].text
            # print(tmp_name)
            if soup_object.dd.find(class_=re.compile(r'field-list')).find_all(class_='field-odd')[-1].find('ul'):
                tmp_content = soup_object.dd.find(class_=re.compile(r'field-list')).find_all(class_='field-odd')[-1].ul.children
            else:
                tmp_content = soup_object.dd.find(class_=re.compile(r'field-list')).find_all(class_='field-odd')[
                    -1].children
            if 'parameter' in tmp_name.lower() or 'keyword arguments' in tmp_name.lower():
                get_dic(tmp_content, parameter_dic)
                # parameter_dic = get_dic(tmp_content)
            elif 'return type' in tmp_name.lower():
                get_dic(tmp_content, attribute_dic)
            elif 'returns' in tmp_name.lower():
                get_dic(tmp_content,return_dic, is_return=True)
            elif 'raises' in tmp_name.lower():
                get_dic(tmp_content, exception_dic)
        except:
            pass

        try:
            tmp_name = soup_object.dd.find(class_=re.compile(r'field-list')).find_all(class_='field-even')[0].text
            if soup_object.dd.find(class_=re.compile(r'field-list')).find_all(class_='field-even')[-1].find('ul'):
                tmp_content = soup_object.dd.find(class_=re.compile(r'field-list')).find_all(class_='field-even')[-1].ul.children
            else:
                tmp_content = soup_object.dd.find(class_=re.compile(r'field-list')).find_all(class_='field-even')[
                    -1].children
            if 'parameter' in tmp_name.lower() or 'keyword arguments' in tmp_name.lower():
                get_dic(tmp_content, parameter_dic)
                # parameter_dic = get_dic(tmp_content)
            elif 'return type' in tmp_name.lower():
                get_dic(tmp_content, attribute_dic)
            elif 'returns' in tmp_name.lower():
                get_dic(tmp_content, return_dic, is_return=True)
            elif 'raises' in tmp_name.lower():
                get_dic(tmp_content, exception_dic)
        except:
            pass


        # Notes
        Notes = ''
        Notes_flag = False
        try:
            for x in list(soup_object.dd.find_all('p')):
                if 'Notes' in str(x) and x.attrs and 'rubric' in x.attrs['class']:
                    Notes_flag = True
                if ('References' in str(x) or 'Examples' in str(x)) and x.attrs and 'rubric' in x.attrs['class']:
                    Notes_flag = False
                if Notes_flag:
                    Notes += remove_prefix(x.text.strip(), 'Notes')
        except:
            pass

        # Examples (code)
        # no examples for matplotlib for now

        Examples = []
        try:
            for example in soup_object.find_all(class_='doctest highlight-default notranslate'):
                Examples.append(example.text.strip())
        except:
            pass

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
        if attribute_dic:
            element_dic['attribute'] = attribute_dic
        if Notes:
            element_dic['note'] = Notes
        if Examples:
            element_dic['examples'] = Examples
        element_dic_list.append(element_dic)
    return element_dic_list, entailment_relationships


# def build_KG_from_html():
#     kg = Graph()
#     namespace_URI = 'https://sklearn-html.org/'
#     html_files = []
#     html_path_list = ['KG_source/pytorch-html/generated/']
#     for html_path in html_path_list:
#         entries = os.listdir(html_path)
#         html_files += [html_path+entry for entry in entries if os.path.isfile(os.path.join(html_path, entry))]
#
#     pass_file_list = []
#
#     for html_file in html_files:
#         print(html_file)
#         # if 'numpy.distutils' in html_file or html_file in pass_file_list:
#         #     continue
#
#         element_dic_list, entailment_relations = get_element_from_html(html_file)
#         if element_dic_list:
#             for element_dic in element_dic_list:
#                 if not element_dic:
#                     continue
#                 print(html_file)
#                 transfer_element_dic_2_triplet(element_dic, kg, namespace_URI)
#
#             entailment_relationship2triplet(entailment_relations, element_dic_list, kg, namespace_URI)
#     return kg


kg = Graph()
namespace_URI = 'https://pytorch-html.org/'

html_files = []
html_path_list = ['KG_source/pytorch-html/generated/']

for html_path in html_path_list:
    entries = os.listdir(html_path)
    html_files += [html_path + entry for entry in entries if os.path.isfile(os.path.join(html_path, entry))]

pass_file_list = []

filter = 'function_only'
api = kg_api.KgAPI()
# flag = False
for html_file in html_files:
    # for html_file in ['KG_source/numpy-html/reference/generated/numpy.distutils.ccompiler.CCompiler_customize.html']:
    print(html_file)
    # if html_file != 'KG_source/numpy-html/reference/generated/numpy.distutils.ccompiler.CCompiler_customize.html' and not flag:
    #     continue
    # else:
    #     flag = True
    # if flag:
    element_dic_list, entailment_relations = get_element_from_html(html_file)
    # element_dic_list = human_modify(html_file, element_dic_list)
    pprint(element_dic_list)
    # break

    if element_dic_list:
        for element_dic in element_dic_list:
            transfer_element_dic_2_triplet_new('pytorch', element_dic, api)



# KG = build_KG_from_html()
# KG.serialize('KG_storage/pytorch_code_KG.ttl', format="turtle")