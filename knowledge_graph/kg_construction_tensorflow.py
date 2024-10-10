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



def get_element_from_html(html_file):
    # html_file = 'KG_source/tensorflow_html/api_docs/python/tf_map_fn.html'
    # html_file = 'KG_source/tensorflow_html/api_docs/python/tf_nn_avg_pool2d.html'
    # html_file = 'KG_source/tensorflow_html/api_docs/python/tf_keras_Layer.html'

    with open(html_file, encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'lxml')
    article_element = soup.find('article', class_='devsite-article')
    if not article_element:
        print('page not available!')
        # return None, None
    element_dic_list = []
    # soup_object_list = get_object_type_new(article_element)
    soup_object = article_element
    # object type

    soup_object_list = [soup_object]
    if len(soup_object_list) >= 1:
        entailment_relationships = relation_analyze(soup_object_list)
    if not soup_object:
        return None, None
    # object name
    if soup_object.find(class_='devsite-page-title'):
        object_name = soup_object.find(class_='devsite-page-title').text
    else:
        object_name = ''
    print(object_name)
    main_body_soup_object = soup_object.find(class_='devsite-article-body')

    # full experssion
    try:
        objects = soup.select('.lang-py.tfo-signature-link')
        object = objects[0].text.strip()
        print(object)
    except:
        return None, None

    # explanation
    object_explanation = ''
    for child in main_body_soup_object.children:
        if child.text.strip():
            # print(child)
            # print('------------------------')
            if child.find(id_='args') is not None:
                break
            if child.name == 'p':
                # print(child)
                # print(child.text.strip())
                object_explanation += child.text.strip()
            if child.text.strip().startswith('Args'):
                  break
    object_explanation = object_explanation.strip()
    print(object_explanation)
    print('-------------')

    # parameters
    parameter_flag = False
    attribute_flag = False
    return_flag = False
    parameter_dic = {}
    return_dic = {}
    attribute_dic = {}
    pid_parameter = 0
    pid_return = 0
    pid_attribute = 0
    for child in main_body_soup_object.children:
        if child.text.strip():
            # print(child)
            # print('------------------------')
            # a = input()

            if child.text.strip().startswith('Args'):
                parameter_flag = True
                attribute_flag = False
                return_flag = False
                continue
            elif child.text.strip().startswith('Attributes'):
                parameter_flag = False
                attribute_flag = True
                return_flag = False
            elif child.text.strip().startswith('Returns'):
                parameter_flag = False
                attribute_flag = False
                return_flag = True
            elif child.text.strip().startswith('Methods'):
                break

            if parameter_flag:
                if child.name == 'tr':
                    parameter_name = ''
                    for td in child.find_all('td'):
                        if td.find('a') and td.a.text.strip() == '' and td.a.has_attr('id'):
                            parameter_name = td.text.strip()
                            parameter_dic[parameter_name] = {}
                        else:
                            if parameter_name in parameter_dic:
                                parameter_dic[parameter_name]['explanation'] = td.text.strip()
                                parameter_dic[parameter_name]['pid'] = pid_parameter
                                pid_parameter += 1
            if attribute_flag:
                if child.name == 'tr':
                    parameter_name = ''
                    for td in child.find_all('td'):
                        if td.find('a') and td.a.text.strip() == '' and td.a.has_attr('id'):
                            parameter_name = td.text.strip()
                            attribute_dic[parameter_name] = {}
                        else:
                            if parameter_name in attribute_dic:
                                attribute_dic[parameter_name]['explanation'] = td.text.strip()
                                attribute_dic[parameter_name]['pid'] = pid_attribute
                                pid_attribute += 1
            if return_flag:
                return_dic['return_0'] = {
                    'explanation': child.text.strip().replace('Returns', '').strip(),
                    'pid': pid_return
                }

    element_dic = {}
    element_dic['object'] = {
        'name': object_name,
        'full_expression': object,
        'explanation': object_explanation,
        'object_type': '',
        'url': html_file
    }
    if parameter_dic:
        element_dic['parameters'] = parameter_dic
    if return_dic:
        element_dic['return'] = return_dic
    if attribute_dic:
        element_dic['attribute'] = attribute_dic
    # if Notes:
    #     element_dic['note'] = Notes
    # if Examples:
    #     element_dic['examples'] = Examples
    element_dic_list.append(element_dic)

    return element_dic_list, entailment_relationships


def transfer_element_dic_2_triplet(library_name, element_dic, kg_api):
    # object
    object_dic = element_dic['object']
    # if filter == 'function_only':
    # if not object_dic['object_type'] in ['method', 'function', 'attribute']:
    #     return
    # private function not include
    if object_dic['full_expression'].startswith('_'):
        return
    kg_api.add_instance_from_dic(element_dic, library_name)


kg = Graph()
namespace_URI = 'https://tensorflow-html.org/'

html_files = []
html_path_list = ['KG_source/tensorflow_html/api_docs/python/']
api = kg_api.KgAPI()

for html_path in html_path_list:
    entries = os.listdir(html_path)
    html_files += [html_path + entry for entry in entries if os.path.isfile(os.path.join(html_path, entry))]

pass_file_list = []

# api = kg_api.KgAPI()
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
    # a = input()

    if element_dic_list:
        for element_dic in element_dic_list:
            transfer_element_dic_2_triplet('tensorflow', element_dic, api)




# namespace_URI = 'https://tensorflow-html.org/'
#
# html_files = []
# html_path_list = ['KG_source/tensorflow-html/api_docs/python/']
# for html_path in html_path_list:
#     entries = os.listdir(html_path)
#     html_files += [html_path+entry for entry in entries if os.path.isfile(os.path.join(html_path, entry))]
#
# pass_file_list = []


# filter = 'function_only'
# api = kg_api.KgAPI()
# # flag = False
# for html_file in html_files:
# # for html_file in ['KG_source/numpy-html/reference/generated/numpy.distutils.ccompiler.CCompiler_customize.html']:
#     print(html_file)
#     # if html_file != 'KG_source/numpy-html/reference/generated/numpy.distutils.ccompiler.CCompiler_customize.html' and not flag:
#     #     continue
#     # else:
#     #     flag = True
#     # if flag:
#     element_dic_list, entailment_relations = get_element_from_html(html_file)
#     # element_dic_list = human_modify(html_file, element_dic_list)
#     pprint(element_dic_list)
#     # break
#     if element_dic_list:
#         for element_dic in element_dic_list:
#             transfer_element_dic_2_triplet_new('sklearn', element_dic, api)