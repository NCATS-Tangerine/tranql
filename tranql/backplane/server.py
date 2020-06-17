"""
Provide a normalized protocol for asking graph oriented questions of Translator data sources.
"""
import copy
import argparse
import json
import logging
import os
import yaml
import jsonschema
import requests
from flask import Flask, request, Response, jsonify
from flask_restful import Api, Resource, abort
from flasgger import Swagger
from flasgger.utils import validate as Validate
from flask_cors import CORS
from tranql.main import TranQL
import networkx as nx
from tranql.util import JSONKit
from tranql.concept import BiolinkModelWalker
from tranql.backplane.iceesclient import ICEES

logger = logging.getLogger (__name__)

app = Flask(__name__)

api = Api(app)
CORS(app)

""" https://github.com/NCATS-Gamma/NCATS-ReasonerStdAPI """
filename = 'translator_interchange.yaml'
filename = os.path.join (os.path.dirname (__file__), 'translator_interchange.yaml')
definitions_filename = os.path.join (os.path.dirname (__file__), 'definitions.yaml')
with open(filename, 'r') as file_obj:
    template = yaml.load(file_obj)
    with open(definitions_filename, 'r') as definitions_file:
        template["definitions"].update(yaml.load(definitions_file))
    template["tags"] = [
        {"name" : "schema"},
        {"name" : "query"},
        {"name" : "publish"}
    ]
app.config['SWAGGER'] = {
    'title': 'TranQL Backplane',
    'description': 'hi',
    'uiversion': 3,
    'openapi': '3.0.1'
}
swagger = Swagger(app, template=template, config={
    "headers": [
    ],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,  # ?
            "model_filter": lambda tag: True,  # ?
        }
    ],
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "openapi": "3.0.1",
    'swagger_ui_bundle_js': 'https://rawcdn.githack.com/swagger-api/swagger-ui/v3.23.1/dist/swagger-ui-bundle.js',
    'swagger_ui_standalone_preset_js': 'https://rawcdn.githack.com/swagger-api/swagger-ui/v3.23.1/dist/swagger-ui-standalone-preset.js',
    'swagger_ui_css': 'https://rawcdn.githack.com/swagger-api/swagger-ui/v3.23.1/dist/swagger-ui.css',
    'swagger_ui_js': 'https://rawcdn.githack.com/swagger-api/swagger-ui/v3.23.1/dist/swagger-ui.js'
})

#######################################################
##
## ICEES - Wrapping ICEES Clinical Reasoner Operations
##
#######################################################
class ICEESClusterArgs:
    def __init__(
            self,
            cohort_id="COHORT:22",
            feature_id="EstResidentialDensity",
            value="1",
            operator=">",
            max_p_val="0.5"):
        self.cohort_id = cohort_id
        self.feature_id = feature_id
        self.value = value
        self.operator = operator
        self.max_p_val = max_p_val

class StandardAPIResource(Resource):
    @staticmethod
    def validate (request, definition, no_abort=False):
        if not isinstance(request,dict):
            request = request.json

        valid = True
        try:
            pass
            # For some reason this method doesn't work...
            # Validate(request, definition, specs=template)
        except Exception as e:
            valid = False

        if no_abort:
            return valid

        if not valid:
            abort(
                500,
                message="Invalid "+definition,
                status="error",
                code="invalid_arguments"
            )

    def get_opt (self, request, opt):
        return request.get('option', {}).get (opt)
    def rename_key (self, obj, old, new, default=None):
        if old in obj:
            obj[new] = obj.pop (old)
    def rename_key_list (self, node_list, old, new):
        for n in node_list:
            self.rename_key (n, old, new)
    def format_as_query(self, message):
        question_graph = message['question_graph']

        for node in question_graph.get('nodes',[]):
            node['node_id'] = node['id']
            del node['id']
        for edge in question_graph.get('edges',[]):
            edge['edge_id'] = edge['id']
            del edge['id']

        return {
            "query_message": {
                "query_graph": question_graph
            }
        }
    def merge_results (self, message):
        results = message['results']
        del message['results']
        if 'knowledge_graph' not in message:
            message['knowledge_graph'] = {
                "edges": [],
                "nodes": []
            }
        if 'knowledge_map' not in message:
            message['knowledge_map'] = []
        nodeIds = []
        for result in results:
            # Convert 0.9.0 equivalent of knowledge_map to the knowledge_map format we want
            node_bindings = result.get('node_bindings',{})
            edge_bindings = result.get('edge_bindings',{})

            if node_bindings != None and edge_bindings != None:
                message['knowledge_map'].append({
                    "node_bindings": node_bindings,
                    "edge_bindings": edge_bindings
                })


            result = result.get('result_graph', {})

            nodes = result.get('nodes',[])
            edges = result.get('edges',[])

            message['knowledge_graph']['edges'].extend(edges)
            for node in nodes:
                if not node['id'] in nodeIds:
                    message['knowledge_graph']['nodes'].append(node)
                    nodeIds.append(node['id'])
        return message

    def down_cast_message(self, message, reasoner_spec_version='2.0', down_cast_to='0.9'):
        if reasoner_spec_version == '2.0':
            assert 'query_graph' in message
            assert 'knowledge_graph' in message
            assert 'results' in message
            if down_cast_to == '0.9':
                converted_results = []
                for r in message['results']:
                    node_bindings = r['node_bindings']
                    edge_bindings = r['edge_bindings']
                    # Expecting
                    # {qg_id: 'qg-id-value', kg_id: 'kg-id-value'}
                    # tranform to {'qg-id-value': 'kg-id-value'}
                    node_bindings = {n['qg_id']: n['kg_id']for n in node_bindings}
                    edge_bindings = {e['qg_id']: e['kg_id']for e in edge_bindings}
                    r['node_bindings'] = node_bindings
                    r['edge_bindings'] = edge_bindings
                    converted_results.append(r)
                message['results'] = converted_results
                return self.normalize_message(message)

    def normalize_message (self, message):
        if 'results' in message:
            return self.normalize_message(self.merge_results(message))
        if 'answers' in message:
            #message['knowledge_map'] = message['answers']
            message['knowledge_map'] = message.pop ('answers')
        #print (f"---- message ------------> {json.dumps(message, indent=2)}")

        ''' downcast 0.9.1 to 0.9 '''
        ''' alter once tranql AST speaks 0.9.1 '''
        self.rename_key (message, old='query_graph', new='question_graph')
        self.rename_key (message, old='machine_question', new='question_graph')
        self.rename_key (message, old='query_options', new='options')
        if not 'knowledge_graph' in message:
            message['knowledge_graph'] = message.get('return value',{}).get('knowledge_graph', {})
        ''' SPEC: for icees, it's machine_question going in and question_graph coming out (but in a return value)? '''
        ''' return value is only an issue for ICEES '''
        if not 'knowledge_map' in message:
            message['knowledge_map'] = message.get('return value',{}).get('answers', [])
        if not 'question_graph' in message:
            message['question_graph'] = message.get('return value',{}).get('question_graph', {})
        self.rename_key_list (message.get('question_graph',{}).get('nodes',[]),
                              old='node_id',
                              new='id')
        self.rename_key_list (message.get('question_graph',{}).get('edges',[]),
                              old='edge_id',
                              new='id')
        #print (f"---- message ------------> {json.dumps(message, indent=2)}")
        return message
    @staticmethod
    def response(data):
        status_code = 200

        # is_error = StandardAPIResource.validate(data, 'Error', no_abort=True)
        is_error = isinstance(data,dict) and 'status' in data and 'code' in data and 'message' in data

        if is_error:
            status_code = 500

        return (data, status_code)
class ICEESSchema(StandardAPIResource):
    def __init__(self):
        self.version_to_url_map = {
            "icees": "https://icees.renci.org/2.0.0/knowledge_graph/schema",
            "icees3_and_epr": "https://icees.renci.org:16339/knowledge_graph/schema"
        }

    def get(self):
        """
        ICEES schema
        ---
        tags: [schema]
        description: Query the ICEES clinical reasoner for associations between population clusters and chemicals.
        responses:
            '200':
                description: Schema
                content:
                    application/json:
                        schema:
                            type: object
                            example:
                                population_of_individual_organisms:
                                    phenotypic_feature:
                                        - association
                                    named_thing:
                                        - association
                                    activity_and_behavior:
                                        - association
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'
        """
        icees_version = request.args.get('provider')
        if not icees_version:
            self.response({
                "status": "error",
                "code" : "400",
                "message": "Bad request. Need to provide version as get parameter."
            })

        self.schema_url = self.version_to_url_map.get(icees_version)
        if not self.schema_url:
            self.response({
                "status": "error",
                "code": "500",
                "message": f"The specified ICEES version could not be found - {icees_version}"
            })
        response = requests.get (
            self.schema_url,
            verify=False)
        if not response.ok:
            return self.response({
                "status" : "error",
                "code"   : "service_invocation_failure",
                "message" : f"Bad ICEES schema response. url: {self.schema_url} request: {request.json} response: {response.text}."
            })
        elif 'return value' in response.json():
            return self.response(response.json()['return value'])
        else:
            return self.response({
                'status' : 'error',
                'message' : 'Unrecognized response from ICEES schema',
                'code' : 'service_invocation_failure'
            })

class ICEESClusterQuery(StandardAPIResource):
    """ ICEES Resource. """
    def __init__(self):
        self.version_to_url_map = {
            "icees": "https://icees.renci.org/2.0.0/knowledge_graph",
            "icees3_and_epr": "https://icees.renci.org:16339/knowledge_graph"
        }

    def post(self):
        """
        ICEES query
        ---
        tags: [query]
        description: Query the ICEES clinical reasoner for associations between population clusters and chemicals.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
                    example:
                        knowledge_graph:
                            nodes: []
                            edges: []
                        knowledge_maps:
                            - {}
                        question_graph:
                            nodes:
                                - id: "cohort_diagnosis"
                                  type: "disease"
                                  curie: "MONDO:0004979"
                                - id: "diagnoses"
                                  type: "disease"
                            edges:
                                - id: "e1"
                                  source_id: "cohort_diagnosis"
                                  target_id: "diagnoses"
                        options:
                            Sex:
                                - "="
                                - "0"
                            cohort:
                                - "="
                                - "all_patients"
                            max_p_value:
                                - "="
                                - "1"


        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            ref: '#/definitions/Message'
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'

        """
        self.validate(request, 'Message')
        icees_version = request.args.get('provider', 'icees')
        #print (f"{json.dumps(request.json, indent=2)}")
        request.json['options'] = self.compile_options (request.json['options'])

        ''' Give ICEES the spec version it wants.
        We have multiple versions of the spec live at once.
        Until these stabilize and converge, we adapt between them in various ways.
        '''

        for e in request.json['question_graph']['edges']:
            e['type'] = 'association'
        request.json['query_options'] = request.json.pop('options')
        request.json['machine_question'] = request.json.pop('question_graph')
        for bad in [ 'knowledge_graph', 'knowledge_maps' ]:
            if bad in request.json:
                 del request.json[bad]

        result = {}

        ''' Invoke ICEES '''
        icees_kg_url = self.version_to_url_map.get(icees_version) #"https://icees.renci.org/2.0.0/knowledge_graph"
        if not icees_version:
            self.response({
                "status": "error",
                "code": "500",
                "message": f"The specified ICEES version could not be found - {icees_version}"
            })
        app.logger.debug (f"--request.json({icees_kg_url})--> {json.dumps(request.json, indent=2)}")
        response = requests.post (icees_kg_url,
                                  json=request.json,
                                  verify=False)

        # with open ('icees.out', 'w') as stream:
        #     json.dump (response.json (), stream, indent=2)
        # app.logger.debug (f"-- response --> {json.dumps(response.json(), indent=2)}")

        response_json = response.json ()
        its_an_error = response_json.\
                       get('return value',{}).\
                       get ('message_code',None) == 'Error'
        if response.status_code >= 300 or its_an_error:
            result = {
                "status" : "error",
                "code"   : "service_invocation_failure",
                "message" : f"Bad ICEES response. url: {icees_kg_url} request: {request.json} response: {response.text}.",
                "query"  : request.json,
                "response" : response_json
            }
            print (f"ICEES-ERROR: {json.dumps(result,indent=2)}")
        else:
            print (f"ICEES-NOMINAL: {json.dumps(result,indent=2)}")
            result = self.normalize_message (response_json)

        with open ('icees.out.norm', 'w') as stream:
            json.dump (result, stream, indent=2)

        return self.response(result)

    def compile_options (self, options):
        """ Compile input options into icees appropriate format. """
        result = {}
        for k in options.keys ():
            val = options[k]
            if '.' in k:
                ''' Make a nested structure. Turn `icees.feature.X = y` into a nested dict. '''
                levels = k.split ('.')
                obj = result
                for index, level in enumerate(levels):
                    if index < len(levels) - 1:
                        last = obj
                        obj = obj.get(level, {}) if level != 'feature' else {} # we only allow one feature, last feature
                                                                               # is the winner
                        last[level] = obj
                    else:
                        obj[level] = {
                            'operator' : val[0],
                            'value'    : val[1]
                        }
            else:
                ''' assign directly. '''
                result[k] = val[1]

        """ Filter ids returned by ICEES to ones we can currently make use of. """
        #result["regex"] = "(MONDO|HP):.*"

        return result

#######################################################
##
## NDEx - publish a graph to NDEx
##
#######################################################
class PublishToNDEx(StandardAPIResource):
    """ Publish a graph to NDEx. """
    def __init__(self):
        super().__init__()

    def post(self):
        """
        Publish a graph to NDEx
        ---
        tags: [publish]
        description: Publish a graph to NDEx.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
        responses:
            '200':
                description: Success
                content:
                    text/plain:
                        schema:
                            type: string
                            example: "Successfully validated"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string
        """
        self.validate (request, 'Message')
        name = request.json.get('options', {}).get ('name', None)
        if name is not None:
            ndex = NDEx ()
            ndex.publish_graph (
                name=name,
                graph={
                    "nodes" : request.json['knowledge_graph']['nodes'],
                    "edges" : request.json['knowledge_graph']['edges']
                })

class RtxQuery(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.base_url = 'https://rtx.ncats.io'
        self.query_url = f'{self.base_url}/beta/api/rtx/v1/query'
    """
    Rtx seems to divulge from the normal identifer syntax in some places so our syntax to be compliant with theirs.
    """
    @staticmethod
    def convert_curies_to_rtx(message):
        for i in message["question_graph"]:
            for element in message["question_graph"][i]:
                if 'curie' in element:
                    curie = element['curie']
                    identifierSource = curie.split(":")
                    if identifierSource[0] == "CHEMBL":
                        curie = "CHEMBL.COMPOUND:"+identifierSource[1]
                    # print(element['curie'],curie)
                    element['curie'] = curie
        return message
    """
    We must convert these curies back to the standard form when returning the response.
    """
    @staticmethod
    def convert_curies_to_standard(message):
        # i = node_bindings, edge_bindings
        for i in message["knowledge_map"]:
            # n = question_graph=>knowledge_graph ids
            for n in i:
                # k = question_graph id
                for k in i[n]:
                    # binding = knowledge_graph ids
                    for enum, binding in enumerate(i[n][k]):
                        identifierSource = binding.split(":")
                        if identifierSource[0] == "CHEMBL.COMPOUND":
                            binding = "CHEMBL:"+identifierSource[1]
                        # print(element['curie'],curie)
                        i[n][k][enum] = binding
                    if n == "node_bindings":
                        i[n][k] = i[n][k][0]
                        # {"disease" : ["chembl:x"]} becomes {"disease" : "chembl:x"}
        for element in message["knowledge_graph"]["nodes"]:
            identifierSource = element["id"].split(":")
            if identifierSource[0] == "CHEMBL.COMPOUND":
                element["id"] = "CHEMBL:"+identifierSource[1]
        for element in message["knowledge_graph"]["edges"]:
            for prop in ["source_id","target_id"]:
                identifierSource = element[prop].split(":")
                if identifierSource[0] == "CHEMBL.COMPOUND":
                    element[prop] = "CHEMBL:"+identifierSource[1]
        for element in message["question_graph"]["nodes"]:
            if "curie" not in element: continue
            identifierSource = element["curie"].split(":")
            if identifierSource[0] == "CHEMBL.COMPOUND":
                element["curie"] = "CHEMBL:"+identifierSource[1]
        return message
    def post(self):
        """
        RTX query
        ---
        tags: [query]
        description: Query the RTX reasoner.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
                    example:
                        knowledge_graph:
                            nodes: []
                            edges: []
                        knowledge_maps:
                            - {}
                        question_graph:
                            nodes:
                                - id: "chemical_substance"
                                  type: "chemical_substance"
                                  curie: "CHEMBL:CHEMBL3"
                                - id: "protein"
                                  type: "protein"
                            edges:
                                - id: "e1"
                                  source_id: "chemical_substance"
                                  target_id: "protein"
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Message'
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'
        """
        self.validate(request, 'Message')

        data = self.format_as_query(self.convert_curies_to_rtx(request.json))
        # print(json.dumps(data,indent=2))
        response = requests.post(self.query_url, json=data)
        if not response.ok:
            if response.status_code == 500:
                result = {
                    "status" : "error",
                    "code"   : "service_invocation_failure",
                    "message" : f"Rtx Internal Server Error. url: {self.query_url} \n request: {json.dumps(data, indent=2)} \nresponse: \n{response.text}\n (code={response.status_code})."
                }
            else:
                result = {
                    "status" : "error",
                    "code"   : "service_invocation_failure",
                    "message" : f"Bad Rtx query response. url: {self.query_url} \n request: {json.dumps(data, indent=2)} \nresponse: \n{response.text}\n (code={response.status_code})."
                }
        else:
            result = self.convert_curies_to_standard(self.normalize_message(response.json()))
        return self.response(result)

class IndigoQuery(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.base_url = 'https://indigo.ncats.io'
        self.query_url = f'{self.base_url}/reasoner/api/v1/query'
    def post(self):
        """
        Indigo query
        ---
        tags: [query]
        description: Query the Indigo reasoner.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
                    example:
                        knowledge_graph:
                            nodes: []
                            edges: []
                        knowledge_maps:
                            - {}
                        question_graph:
                            nodes:
                                - id: "n0"
                                  type: "chemical_substance"
                                  curie: "CHEMBL:CHEMBL521"
                                - id: "n1"
                                  type: "protein"
                            edges:
                                - id: "e1"
                                  source_id: "n0"
                                  target_id: "n1"
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Message'
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'
        """
        self.validate(request, 'Message')

        data = self.format_as_query(request.json)

        # print("input",json.dumps(data,indent=2))
        response = requests.post(self.query_url, json=data)
        if not response.ok:
            if response.status_code == 500:
                result = {
                    "status" : "error",
                    "code"   : "service_invocation_failure",
                    "message" : f"Indigo Internal Server Error. url: {self.query_url} \n request: {json.dumps(data, indent=2)} \nresponse: \n{response.text}\n (code={response.status_code})."
                }
            else:
                result = {
                    "status" : "error",
                    "code"   : "service_invocation_failure",
                    "message" : f"Bad Indigo query response. url: {self.query_url} \n request: {json.dumps(data, indent=2)} \nresponse: \n{response.text}\n (code={response.status_code})."
                }
        else:
            json = response.json()
            if "question_graph" not in json:
                json["question_graph"] = request.json.get('question_graph')
            result = self.normalize_message(json)
        return self.response(result)

#######################################################
##
## Gamma - publish a graph to Gamma.
##
#######################################################
class GammaResource(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.robokop_url = 'https://robokop.renci.org' # TODO - make a configuration setting.
        self.view_post_url = f'{self.robokop_url}/api/simple/view/'
        self.quick_url = f'{self.robokop_url}/api/simple/quick/?rebuild=false&output_format=MESSAGE&max_connectivity=0&max_results=300'
        #                                                      ?rebuild=false&output_format=MESSAGE&max_connectivity=0&max_results=250
    def view_url (self, uid):
        return f'{self.robokop_url}/simple/view/{uid}'

class GammaQuery(GammaResource):
    """ Generic graph query to Gamma. """
    def __init__(self):
        super().__init__()
    def post(self):
        """
        Robokop query
        ---
        tags: [query]
        description: Query the Robokop reasoner.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
                    example:
                        knowledge_graph:
                            nodes: []
                            edges: []
                        knowledge_maps:
                            - {}
                        question_graph:
                            nodes:
                                - id: "chemical_substance"
                                  type: "chemical_substance"
                                  curie: "CHEMBL:CHEMBL3"
                                - id: "disease"
                                  type: "disease"
                            edges:
                                - id: "e1"
                                  source_id: "chemical_substance"
                                  target_id: "disease"
                        options: {}
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Message'
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'
        """
        self.validate (request, 'Message')
        result = {}
        del request.json['knowledge_graph']
        del request.json['knowledge_maps']
        del request.json['options']
        app.logger.debug (f"Making request to {self.quick_url}")
        app.logger.debug (json.dumps(request.json, indent=2))
        response = requests.post (self.quick_url, json=request.json, verify=False)
        # print (f"{json.dumps(response.json (), indent=2)}")
        if response.status_code >= 300:
            result = {
                "status" : "error",
                "code"   : "service_invocation_failure",
                "message" : f"Bad Gamma quick response. url: {self.robokop_url} \n request: {json.dumps(request.json, indent=2)} response: \n{response.text}."
            }
        else:
            result = self.normalize_message (response.json ())
        if app.logger.isEnabledFor(logging.DEBUG):
            app.logger.debug (json.dumps(result, indent=2))
        return self.response(result)

class PublishToGamma(GammaResource):
    """ Publish a graph to Gamma. """
    def __init__(self):
        super().__init__()
    def post(self):
        """
        Publish a graph to Robokop
        ---
        tags: [publish]
        description: Publish a graph to the Gamma viewer.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
        responses:
            '200':
                description: Success
                content:
                    text/plain:
                        schema:
                            type: string
                            example: "Successfully validated"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string
        """

        """ This is just a pass-through to simplify workflows. """
        self.validate (request, 'Message')
        '''
        with open ("gamma_vis.json", "w") as stream:
            json.dump (request.json, stream, indent=2)
        return {}
        '''
        if 'knowledge_map' in request.json:
            request.json['answers'] = request.json['knowledge_map']
            del request.json['knowledge_map']
        #print (f"{json.dumps(request.json, indent=2)}")
        view_post_response = requests.post(
            self.view_post_url,
            json=request.json)
        if view_post_response.status_code >= 300:
            print(f"{view_post_response}")
            raise Exception("Bad response view post")
        uid = json.loads(view_post_response.text)
        print(f"view-post-response: {view_post_response}")
        print(f"view-url: {self.view_url(uid)}")

class GNBRReasoner:
    def query (self, message):
        url=f'https://gnbr-reason.ncats.io/decorator'
        response = requests.post(url,json=message)
        print( f"Return Status: {response.status_code}" )
        result = {}
        if response.status_code == 200:
            result = response.json()
        return result

class GNBRDecorator(StandardAPIResource):
    """ GNBR Knowledge Graph annotator."""
    def post(self):
        """
        Decorate a knowledge graph via GNBR.
        ---
        tags: [query]
        description: GNBR decorator.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Message'

        """
        # self.validate (request)


        knowledge_graph = request.json['knowledge_graph']

        mapped_message = {
            'result_graph': {
                'edge_list': [],
                'node_list': []
            }
        }
        for edge in knowledge_graph['edges']:
            edge['publications'] = edge.get('publications', '')
            if isinstance(edge['publications'],list):
                edge['publications'] = ','.join(edge['publications'])
            mapped_message['result_graph']['edge_list'].append(edge)

        for node in knowledge_graph['nodes']:
            mapped_message['result_graph']['node_list'].append(node)

        rtx = {
            'result_list': [
                mapped_message
            ]
        }

        # Specify result number in range 0-4
        index = 0

        rtx_result = rtx['result_list'][index]
        for edge in rtx_result['result_graph']['edge_list']:
            edge['publications'] = edge.get('publications', [])
            if isinstance(edge['publications'],str):
                edge['publications'] = list(edge['publications'].split(','))
        for node in rtx_result['result_graph']['node_list']:
            if not isinstance(node['type'], list):
                node['type'] = [node['type']]
        node_list = rtx_result['result_graph']['node_list']
        edge_list = rtx_result['result_graph']['edge_list']

        gnbr_reasoner = GNBRReasoner ()
        return gnbr_reasoner.query ({
            "query_message": {
                "query_graph": {
                    'nodes': node_list,
                    'edges': edge_list
                }
            }
        })

class BiolinkModelWalkerService(StandardAPIResource):
    """ Biolink Model Walk Resource. """
    def __init__(self):
        super().__init__()

    def post(self):
        """
        biolink-model conversions.
        ---
        tags: [query]
        description: Convert biolink model types.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Message'

        """
        self.validate (request, 'Message')
        question = request.json['question_graph']
        question_nodes = question['nodes']
        source_node = question_nodes[0]
        target_node = question_nodes[1]
        target_type = target_node['type']
        response = copy.deepcopy (request.json)
        if len(question_nodes) == 2:
            biolink_model_walker = BiolinkModelWalker ()
            conversion = biolink_model_walker.translate (
                node=source_node,
                target_type=target_type)
            if conversion is not None:
                response['knowledge_graph'] = {
                    "nodes" : [ conversion ],
                    "edges" : []
                }
                response['answers'] = [
                    {
                        'node_bindings' : {
                            target_type : conversion['id']
                        }
                    }
                ]
            else:
                raise ValueError (f"Unable to convert {source_node} to {target_type}")
            print (json.dumps(response, indent=2))
        if not 'answers' in response:
            response['answers'] = []
        return self.normalize_message (response)

#######################################################
##
## Automat - query Automat-KPs.
##
#######################################################

class AutomatResource(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.url = 'https://automat.renci.org'

    def get_kp_reasoner_api(self, kp_tag):
        return f'{self.url}/{kp_tag}/reasonerapi'

class AutomatQuery(AutomatResource):
    """ Generic graph query to Gamma. """
    def __init__(self):
        super().__init__()
    def post(self, kp_tag):
        """
        Automat query
        ---
        tags: [query]
        description: Query the Automat KPs.
        parameters:
            - in: path
              name: kp_tag
              schema:
                type: string
                example: uberon
              required: true
              description: KP identifier to get data from.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
                    example:
                        knowledge_graph:
                            nodes: []
                            edges: []
                        knowledge_maps:
                            - {}
                        question_graph:
                            nodes:
                                - id: "chemical_substance"
                                  type: "chemical_substance"
                                  curie: "CHEMBL:CHEMBL3"
                                - id: "disease"
                                  type: "disease"
                            edges:
                                - id: "e1"
                                  source_id: "chemical_substance"
                                  target_id: "disease"
                        options: {}

        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Message'
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'
        """
        self.validate (request, 'Message')
        url = self.get_kp_reasoner_api(kp_tag)
        app.logger.debug(f"Making request to {url}")
        # question_graph should be query graph
        question = request.json
        question['query_graph'] = copy.deepcopy(question['question_graph'])
        del question['question_graph']
        del question['knowledge_graph']
        del question['knowledge_maps']
        app.logger.debug (json.dumps(question, indent=2))

        response = requests.post(url, json=question)
        if response.status_code >= 300:
            result = {
                "status" : "error",
                "code"   : "service_invocation_failure",
                "message" : f"Bad Automat response. url: {self.url} \n request: {json.dumps(request.json, indent=2)} response: \n{response.text}."
            }
        else:
            result = self.down_cast_message (response.json ())
        if app.logger.isEnabledFor(logging.DEBUG):
            app.logger.debug (json.dumps(result, indent=2))
        return self.response(result)


###############################################################################################
#
# Define routes.
#
###############################################################################################

#api.add_resource(TranQLQuery, '/graph/tranql')

# Generic
api.add_resource(GammaQuery, '/graph/gamma/quick')
api.add_resource(BiolinkModelWalkerService, '/implicit_conversion')
api.add_resource(GNBRDecorator, '/graph/gnbr/decorate')
api.add_resource(IndigoQuery, '/graph/indigo')
api.add_resource(RtxQuery, '/graph/rtx')
api.add_resource(AutomatQuery, '/graph/automat/<kp_tag>')

# Workflow specific
api.add_resource(ICEESClusterQuery, '/clinical/cohort/disease_to_chemical_exposure')
api.add_resource(ICEESSchema, '/clincial/icees/schema')

# Visualization
api.add_resource(PublishToGamma, '/visualize/gamma')
api.add_resource(PublishToNDEx, '/visualize/ndex')

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='TranQL Backplane')
    parser.add_argument('--host', action="store", dest="host", default='0.0.0.0')
    parser.add_argument('-p', '--port', action="store", dest="port", default=8099, type=int)
    parser.add_argument('-d', '--debug', help="Debug log level.", default=False, action='store_true')
    parser.add_argument('-r', '--reloader', help="Use reloader independent of debug.", default=False, action='store_true')
    args = parser.parse_args()
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=args.debug or args.reloader
    )
