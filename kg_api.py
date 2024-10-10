import logging
import threading
import os
from SPARQLWrapper import SPARQLWrapper, QueryResult, TURTLE, JSON
import re

class KgAPI:
    # Public static function do not modify at runtime
    _LOG_PATH = os.getcwd() + "/" + "kg_api.log"
    _FUSEKI_URL = "http://localhost:3030/PythonAPI"
    _LOCK = threading.Lock()
    _KNOWLEDGE_BASE = "<#tdbGraph>"
    _KNOWLEDGE_BASE_NUMPY = "<#numpyGraph>"
    _KNOWLEDGE_BASE_PANDAS = "<#pandasGraph>"
    _KNOWLEDGE_BASE_SCIPY = "<#scipyGraph>"
    _KNOWLEDGE_BASE_SKLEARN = "<#sklearnGraph>"
    _KNOWLEDGE_BASE_MATPLOTLIB = "<#matplotlibGraph>"
    _KNOWLEDGE_BASE_PYTORCH = "<#pytorchGraph>"
    _KNOWLEDGE_BASE_TENSORFLOW = "<#tensorflowGraph>"
    _ONTOLOGY_URI = "http://w3id.org/kg4cg/vocab#"
    _NAMESPACE = "kg4cg"
    _GRAPH_URI = "http://w3id.org/kg4cg/data#tdbGraph"
    _BACK_UP_PATH = os.getcwd() + "/" + "backup datadump"
    _PREFIX = "kg4cg"

    def __init__(self):
        self._init_logging()
        self.update_url = KgAPI._FUSEKI_URL
        self.query_url = KgAPI._FUSEKI_URL

    def _select_graph(self, library_name: str) -> str:
        if library_name == 'numpy':
            return self._KNOWLEDGE_BASE_NUMPY
        elif library_name == 'pandas':
            return self._KNOWLEDGE_BASE_PANDAS
        elif library_name == 'scipy':
            return self._KNOWLEDGE_BASE_SCIPY
        elif library_name == 'sklearn':
            return self._KNOWLEDGE_BASE_SKLEARN
        elif library_name == 'tensorflow':
            return self._KNOWLEDGE_BASE_TENSORFLOW
        elif library_name == 'pytorch':
            return self._KNOWLEDGE_BASE_PYTORCH
        elif library_name == 'matplotlib':
            return self._KNOWLEDGE_BASE_MATPLOTLIB
        else:
            return self._KNOWLEDGE_BASE


    def _init_logging(self) -> None:
        """
        Initialize the logging configuration.
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(KgAPI._LOG_PATH),
                logging.StreamHandler()
            ]
        )

    @property
    def prefix(self) -> str:
        prefix = f'''PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX {KgAPI._NAMESPACE}: <{KgAPI._ONTOLOGY_URI}>'''
        return prefix
        # return f"PREFIX {KgAPI._NAMESPACE}: <{KgAPI._ONTOLOGY_URI}>"

    def send_request(self, url, query: str, method: str = "POST", payload=None, return_format=JSON) -> QueryResult:
        """
        Send a SPARQL query to the Fuseki server

        :param url: The URL of the Fuseki server.
        :param query: The SPARQL query to send.
        :return: The response from the server.
        """
        sparql = SPARQLWrapper(url)

        sparql.setMethod(method)
        if query is not None:
            sparql.setQuery(query)

        sparql.setReturnFormat(return_format)

        if payload is not None:
            sparql.setPayload(payload)
        try:
            results = sparql.query()
        except Exception as e:
            logging.error(e)
            return None
            # results = None
        if results.response.code == 200 or results.response.code == 204:
            return sparql.query()
        else:
            logging.error(f"Failed to send request to Fuseki server.\n"
                          f"Response code: {results.response.status_code}\n"
                          f"Response message: {results.response.reason}\n"
                          f"Request sent: {query}\n"
                          )
            return None

    def _get_insert_param_return_query(self, library_name: str, has_name_value: str, kg_class_name: str, explanation: str, pid: str, type: str, kg_object_name: str) -> str:
        """
        Get the query to insert a parameter or return into the knowledge graph.
        """
        knowledge_base_name = self._select_graph(library_name)
        query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX kg4cg: <http://w3id.org/kg4cg/vocab#> 

INSERT DATA {{
    GRAPH {knowledge_base_name} {{
        {KgAPI._PREFIX}:{self._replace_dot_to_underline(kg_object_name)} rdf:type {KgAPI._PREFIX}:{kg_class_name};
            {KgAPI._PREFIX}:hasName "{has_name_value}";
            {KgAPI._PREFIX}:hasExplanation "{explanation}";
            {KgAPI._PREFIX}:hasPid "{pid}"; 
            {KgAPI._PREFIX}:hasType "{type}".
    }}
}}
"""
        return query

    def _get_insert_function_query_basic(self, library_name, module_name, function_name) -> str:
        knowledge_base_name = self._select_graph(library_name)
        query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX kg4cg: <http://w3id.org/kg4cg/vocab#> 

INSERT DATA {{
    GRAPH {knowledge_base_name} {{
        {KgAPI._PREFIX}:{self._replace_dot_to_underline(function_name)} rdf:type {KgAPI._PREFIX}:Function;
            {KgAPI._PREFIX}:hasName "{function_name}";
            {KgAPI._PREFIX}:belongsToModule {KgAPI._PREFIX}:{self._replace_dot_to_underline(module_name)};
            {KgAPI._PREFIX}:belongsToLibrary {KgAPI._PREFIX}:{self._replace_dot_to_underline(library_name)};
    }}
}}
"""
        return query

    def _get_insert_function_query_detail(self, library_name, function_name, explanation, expression, note, parameter_list, return_list) -> str:
        knowledge_base_name = self._select_graph(library_name)
        note_query, parameter_query, return_query = "", "", ""
        if note:
            note_query += f"{KgAPI._PREFIX}:hasNote \"{note}\";" + "\n            "
        for parameter_ in parameter_list:
            parameter_query += f"{KgAPI._PREFIX}:hasParameter {KgAPI._PREFIX}:{parameter_};" + "\n            "
        for return_ in return_list:
            return_query += f"{KgAPI._PREFIX}:hasReturn {KgAPI._PREFIX}:{return_};" + "\n            "

        query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX kg4cg: <http://w3id.org/kg4cg/vocab#>

INSERT DATA {{
    GRAPH {knowledge_base_name} {{
        {KgAPI._PREFIX}:{self._replace_dot_to_underline(function_name)} rdf:type {KgAPI._PREFIX}:Function;
            {KgAPI._PREFIX}:hasName "{function_name}";
            {KgAPI._PREFIX}:hasExplanation "{explanation}";
            {KgAPI._PREFIX}:hasExpression "{expression}";
            {parameter_query}{return_query}{note_query}
    }}
}}
"""
        return query

    def _get_insert_module_query(self, library_name, module_name, function_name) -> str:
        knowledge_base_name = self._select_graph(library_name)
        query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX kg4cg: <http://w3id.org/kg4cg/vocab#> 

INSERT DATA {{
    GRAPH {knowledge_base_name} {{
        {KgAPI._PREFIX}:{self._replace_dot_to_underline(module_name)} rdf:type {KgAPI._PREFIX}:Module;
            {KgAPI._PREFIX}:hasName "{module_name}";
            {KgAPI._PREFIX}:belongsToLibrary {KgAPI._PREFIX}:{library_name};
            {KgAPI._PREFIX}:hasFunction {KgAPI._PREFIX}:{self._replace_dot_to_underline(function_name)};
    }}
}}
"""
        return query

    def _get_insert_library_query(self, library_name, module_name, function_name) -> str:
        knowledge_base_name = self._select_graph(library_name)
        query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX kg4cg: <http://w3id.org/kg4cg/vocab#> 

INSERT DATA {{
    GRAPH {knowledge_base_name} {{
        {KgAPI._PREFIX}:{self._replace_dot_to_underline(library_name)} rdf:type {KgAPI._PREFIX}:Library;
            {KgAPI._PREFIX}:hasName "{library_name}";
            {KgAPI._PREFIX}:hasModule {KgAPI._PREFIX}:{self._replace_dot_to_underline(module_name)};
            {KgAPI._PREFIX}:hasFunction {KgAPI._PREFIX}:{self._replace_dot_to_underline(function_name)};
    }}
}}
"""
        return query

    def _send_update_query_with_logging(self, query, target, target_kg_class):
        response = self.send_request(self.update_url, query)
        if response is not None:
            logging.info(f"{target_kg_class} {target} added to the knowledge graph.")
        else:
            logging.error(f"Failed to add {target_kg_class} {target} to the knowledge graph.")

    def _send_search_query_with_logging(self, query):
        # print('----%s (%s)----' % (target, target_kg_class))
        # print(query)
        # print('--------')
        response = self.send_request(self.query_url, query)
        if response is not None:
            logging.info(f"Query succesfully!")
        else:
            logging.error(f"Failed to query the knowledge graph.")
        return response

    def _replace_special_chars(self, text):
        """
        Helper functon to replace special characters in a string with an empty string.
        """
        pattern = r"[^a-zA-Z0-9_]"
        cleaned_string = re.sub(pattern, "", text)
        return cleaned_string

    def _replace_changeline(self, text):
        # return text.replace('\n', '\\n')
        return text.replace('\n', ' ').replace("\\", "\\\\").replace("\"", "\\\"")

    def _replace_dot_to_underline(self, text):
        return text.replace('.', '_')

    def _add_instance_from_url(self, url) -> None:
        last_part = url.rsplit('/', 1)[-1].replace('.html', '')
        function_name = last_part
        module_name = last_part.rsplit('.', 1)[0]
        library_name = last_part.split('.', 1)[0]

        if module_name == library_name:
            module_name = ''
        else:
            query = self._get_insert_module_query(library_name, module_name, function_name)
            self._send_update_query_with_logging(query, module_name, "Module")

        query = self._get_insert_library_query(library_name, module_name, function_name)
        self._send_update_query_with_logging(query, library_name, "Library")

        query = self._get_insert_function_query_basic(library_name, module_name, function_name)
        self._send_update_query_with_logging(query, function_name, "Function")


    def add_instance_from_dic(self, html_dic, library_name) -> None:
        object_name = html_dic["object"]["name"]

        # add module and function (basic) into knowledge graph
        self._add_instance_from_url(html_dic['object']['url'])
        Parameter_kg_object_list = []
        Return_kg_object_list = []

        # add parameter into knowledge graph
        if "parameters" in html_dic:
            for param_name, details in html_dic["parameters"].items():
                kg_object_name = self._replace_special_chars(self._replace_dot_to_underline(object_name) + '_parameter_' + param_name)

                if 'explanation' in details:
                    param_explanation = details["explanation"]
                else:
                    param_explanation = ''
                param_pid = details["pid"]
                if "type" in details:
                    param_type = details["type"]
                else:
                    param_type = ''
                Parameter_kg_object_list.append(kg_object_name)
                query = self._get_insert_param_return_query(library_name, param_name,
                                                            "Parameter",
                                                            self._replace_changeline(param_explanation),
                                                            param_pid,
                                                            self._replace_changeline(param_type),
                                                            kg_object_name)


                self._send_update_query_with_logging(query, param_name, "Parameter")


        # add return into knowledge graph
        if "return" in html_dic:
            for return_name, details in html_dic["return"].items():
                kg_object_name = self._replace_special_chars(self._replace_dot_to_underline(object_name)  + '_return_' + return_name)
                if "explanation" in details:
                    return_explanation = details["explanation"]
                else:
                    return_explanation = ''
                return_pid = details["pid"]
                if "type" in details:
                    return_type = details["type"]
                else:
                    return_type = ''
                Return_kg_object_list.append(kg_object_name)
                query = self._get_insert_param_return_query(library_name, return_name,
                                                            "Return",
                                                            self._replace_changeline(return_explanation),
                                                            return_pid,
                                                            self._replace_changeline(return_type),
                                                            kg_object_name)
                self._send_update_query_with_logging(query, return_name, "Return")


        if 'note' in html_dic:
            note = html_dic['note']
        else:
            note = ''
        query = self._get_insert_function_query_detail(library_name, object_name,
                                                       self._replace_changeline(html_dic['object']['explanation']),
                                                       self._replace_changeline(html_dic['object']['full_expression']),
                                                       self._replace_changeline(note),
                                                       Parameter_kg_object_list,
                                                       Return_kg_object_list)

        self._send_update_query_with_logging(query, object_name, "Function")

    def query_knowledge_graph(self, query):
        return self._send_search_query_with_logging(self.prefix + '\n' + query)