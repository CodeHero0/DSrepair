import os
from bs4 import BeautifulSoup
import re
from rdflib import Graph, Namespace, Literal, URIRef
import lxml
from rdflib.namespace import RDF, RDFS

from kg_construction_tookit import (get_element_from_html, transfer_element_dic_2_triplet,
                                    get_element_from_code, entailment_relationship2triplet)

from pprint import pprint
import sys
sys.path.append('../')
import kg_api

# numpy version 1.26

# def build_KG_from_html():
#     kg_repair = Graph()
#     namespace_URI = 'https://numpy-html.org/'
#     # html_path = 'numpy-html/reference/generated/'
#     html_files = []
#     html_path_list = ['KG_source/numpy-html/reference/generated/',
#                       'KG_source/numpy-html/reference/random/generated/']
#     for html_path in html_path_list:
#         entries = os.listdir(html_path)
#         html_files += [html_path+entry for entry in entries if os.path.isfile(os.path.join(html_path, entry))]
#
#     # Filter out only files, excluding directories
#     pass_file_list = ['numpy.lib.arraysetops.html', 'numpy.lib.format.html']
#
#     # with open('generated_html_file_classify_numpy.json') as f:
#     #     file_classify = json.load(f)
#
#     # for html_file in file_classify['py class']:
#     for html_file in html_files:
#         print(html_file)
#         # distutils is deprecated
#         # the two files in pass_file_list are content webpage
#         if 'numpy.distutils' in html_file or html_file in pass_file_list:
#             continue
#
#         element_dic = get_element_from_html(html_file)
#         # print(html_path + html_file)
#         # pprint(element_dic)
#         transfer_element_dic_2_triplet(element_dic, kg_repair, namespace_URI)
#     return kg_repair

# def build_KG_from_html():
#     kg = Graph()
#     namespace_URI = 'https://numpy-html.org/'
#     # html_path = 'numpy-html/reference/generated/'
#     html_files = []
#     html_path_list = ['KG_source/numpy-html/reference/generated/',
#                       'KG_source/numpy-html/reference/random/generated/']
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

def build_KG_from_code():
    kg = Graph()
    namespace_URI = 'https://numpy-code.org/'
    folder_path = 'numpy-code/numpy/'
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py") or file.endswith('pyx'):
                print(os.path.join(root, file))
                # element_dic_list = get_element_from_code('./numpy-code/numpy/_core/getlimits.py')
                element_dic_list = get_element_from_code(os.path.join(root, file))
                for element_dic in element_dic_list:
                    transfer_element_dic_2_triplet(element_dic, kg, namespace_URI)
    return kg



# kg_repair = Graph()
# namespace_URI = 'https://numpy-code.org/'
# folder_path = './numpy-code/numpy/'
# element_dic_list = get_element_from_code('./numpy-code/numpy/_core/multiarray.py')
# for element_dic in element_dic_list:
#     transfer_element_dic_2_triplet(element_dic, kg_repair, namespace_URI)

# tmp = get_element_from_code('./numpy-code/numpy/_core/getlimits.py')


# numpy_code_KG = build_KG_from_html()

def transfer_element_dic_2_triplet_new(library_name, element_dic, kg_api, filter='function_only'):
    # object
    object_dic = element_dic['object']
    if filter == 'function_only':
        if not object_dic['object_type'] in ['method', 'function', 'attribute']:
            return
        # private function not include
        if object_dic['full_expression'].startswith('_'):
            return
        kg_api.add_instance_from_dic(element_dic, library_name)


def human_modify(html_file, element_dic_list):
    if html_file == 'KG_source/numpy-html/reference/generated/numpy.distutils.ccompiler_opt.CCompilerOpt.feature_names.html':
        element_dic_list = [{'object': {'explanation': '',
             'full_expression': 'distutils.ccompiler_opt.CCompilerOpt.feature_names(names=None, '
                                'force_flags=None, macros=[])',
             'name': 'numpy.distutils.ccompiler_opt.CCompilerOpt.feature_names',
             'object_type': 'method',
             'url': 'KG_source/numpy-html/reference/generated/numpy.distutils.ccompiler_opt.CCompilerOpt.feature_names.html'},
              'parameters': {'force_flags': {'explanation': 'If None(default), default '
                                                'compiler flags for every CPU '
                                                'feature will\n'
                                                'be used during the test.',
                                 'pid': '1',
                                 'type': 'list or None, optional'},
                 'macros': {'explanation': 'A list of C macro definitions.',
                            'pid': '2',
                            'type': 'list of tuples, optional'},
                 'names': {'pid': '0',
                           'type': 'sequence or None, optional',
                           'explanation': 'Specify certain CPU features to test it against the C compiler.\nif None(default), it will test all current supported features.\nNote: feature names must be in upper-case.'
                 }}}]
    return element_dic_list


def build_KG_from_html():
    kg = Graph()
    namespace_URI = 'https://numpy-html.org/'
    # html_path = 'numpy-html/reference/generated/'
    html_files = []
    html_path_list = ['KG_source/numpy-html/reference/generated/',
                      'KG_source/numpy-html/reference/random/generated/']
    for html_path in html_path_list:
        entries = os.listdir(html_path)
        html_files += [html_path+entry for entry in entries if os.path.isfile(os.path.join(html_path, entry))]

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
        element_dic_list = human_modify(html_file, element_dic_list)
        pprint(element_dic_list)
        # break
        if element_dic_list:
            for element_dic in element_dic_list:
                transfer_element_dic_2_triplet_new('numpy', element_dic, api)
        #         if not element_dic:
        #             continue
        #         print(html_file)
        #
        #         # transfer_element_dic_2_triplet_new(element_dic, api, filter)
        #
        #     entailment_relationship2triplet(entailment_relations, element_dic_list, kg, namespace_URI)

html_file = 'KG_source/numpy-html/reference/generated/numpy.empty.html'
element_dic_list, entailment_relations = get_element_from_html(html_file)