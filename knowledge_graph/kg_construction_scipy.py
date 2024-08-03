import os
from bs4 import BeautifulSoup
import re
from rdflib import Graph, Namespace, Literal, URIRef
import lxml
from kg_construction_tookit import (get_element_from_html, transfer_element_dic_2_triplet,
                                    entailment_relationship2triplet, transfer_element_dic_2_triplet_new)
from pprint import pprint
import sys
sys.path.append('../')
import kg_api

# scipy version: 1.12.0

# def build_KG_from_html():
#     kg_repair = Graph()
#     namespace_URI = 'https://scipy-html.org/'
#     html_files = []
#     html_path_list = ['KG_source/scipy-html/reference/generated/']
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
#         element_dic = get_element_from_html(html_file)
#         if not element_dic:
#             continue
#         # print(html_path + html_file)
#         # pprint(element_dic)
#         transfer_element_dic_2_triplet(element_dic, kg_repair, namespace_URI)
#     return kg_repair

# def build_KG_from_html():
#     kg = Graph()
#     namespace_URI = 'https://scipy-html.org/'
#     html_files = []
#     html_path_list = ['KG_source/scipy-html/reference/generated/']
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
namespace_URI = 'https://scipy-html.org/'
# html_path = 'numpy-html/reference/generated/'
html_files = []
html_path_list = ['KG_source/scipy-html/reference/generated/']
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
            transfer_element_dic_2_triplet_new('scipy', element_dic, api)


# a = build_KG_from_html()
# a.serialize('KG_storage/scipy_html_KG.ttl', format="turtle")
# html_file = 'scipy-html/reference/generated/scipy.special.ellipkinc.html'
# element_dic = get_element_from_html(html_file)