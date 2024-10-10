import os
from bs4 import BeautifulSoup
import re
from rdflib import Graph, Namespace, Literal, URIRef
import lxml
from kg_construction_tookit import (get_element_from_html, transfer_element_dic_2_triplet,
                                    entailment_relationship2triplet, transfer_element_dic_2_triplet_new)
from pprint import pprint
import sys
# sys.path
sys.path.append('../')
import kg_api
# matplotlib version: 3.8.2

# def build_KG_from_html():
#     kg = Graph()
#     namespace_URI = 'https://matplotlib-html.org/'
#     html_files = []
#     html_path_list = ['KG_source/matplotlib-html/api/_as_gen/']
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
namespace_URI = 'https://matplotlib-html.org/'

html_files = []
html_path_list = ['KG_source/matplotlib-html/api/_as_gen/']
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
            transfer_element_dic_2_triplet_new('matplotlib', element_dic, api)



# html_file = 'KG_source/matplotlib-html/api/_as_gen/matplotlib.axes.Axes.eventplot.html'
# html_file = 'KG_source/matplotlib-html/api/_as_gen/matplotlib.markers.MarkerStyle.html'

# element_dic_list, entailment_relations = get_element_from_html(html_file)
# kg_repair = Graph()
# namespace_URI = 'https://matplotlib-html.org/'
# entailment_relationship2triplet(entailment_relations, element_dic_list, kg_repair, namespace_URI)
# transfer_element_dic_2_triplet(a1[0], kg_repair, namespace_URI)
# a = build_KG_from_html()
# a.serialize('KG_storage/matplotlib_code_KG.ttl', format="turtle")