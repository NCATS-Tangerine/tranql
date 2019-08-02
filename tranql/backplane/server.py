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
from flask import Flask, request, abort, Response
from flask_restful import Api, Resource
from flasgger import Swagger
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
filename = os.path.join (os.path.dirname (__file__), 'translator_interchange_0.9.0.yaml')
with open(filename, 'r') as file_obj:
    template = yaml.load(file_obj)
app.config['SWAGGER'] = {
    'title': 'TranQL Backplane',
    'description': 'hi',
    'uiversion': 3
}
swagger = Swagger(app, template=template)

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
    def validate (self, request):
        with open(filename, 'r') as file_obj:
            specs = yaml.load(file_obj)
        to_validate = specs["components"]["schemas"]["Message"]
        to_validate["components"] = specs["components"]
        to_validate["components"].pop("Message", None)
        try:
            jsonschema.validate(request.json, to_validate)
        except jsonschema.exceptions.ValidationError as error:
            print (f"ERROR: {str(error)}")
            abort(Response(str(error), 400))
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
            node_bindings = result.get('node_bindings',None)
            edge_bindings = result.get('edge_bindings',None)
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
class ICEESSchema(StandardAPIResource):
    def __init__(self):
        self.schema_url = "https://icees.renci.org/2.0.0/knowledge_graph/schema"
    def get(self):
        """
        schema
        ---
        tag: validation
        description: Query the ICEES clinical reasoner for associations between population clusters and chemicals.
        responses:
            '200':
                description: Success
                content:
                    application/json:
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
        response = requests.get (
            self.schema_url,
            verify=False)
        if not response.ok:
            return {
                "status" : "error",
                "code"   : "service_invocation_failure",
                "message" : f"Bad ICEES schema response. url: {self.schema_url} request: {request.json} response: {response.text}."
            }
        elif 'return value' in response.json():
            return response.json()['return value']
        else:
            return {
                'status' : 'error',
                'message' : 'Unrecognized response from ICEES schema',
                'code' : 'service_invocation_failure'
            }

class ICEESClusterQuery(StandardAPIResource):
    """ ICEES Resource. """

    def post(self):
        """
        query
        ---
        tag: validation
        description: Query the ICEES clinical reasoner for associations between population clusters and chemicals.
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
        self.validate (request)
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
        icees_kg_url = "https://icees.renci.org/2.0.0/knowledge_graph"
        app.logger.debug (f"--request.json({icees_kg_url})--> {json.dumps(request.json, indent=2)}")
        response = requests.post (icees_kg_url,
                                  json=request.json,
                                  verify=False)

        with open ('icees.out', 'w') as stream:
            json.dump (response.json (), stream, indent=2)
        app.logger.debug (f"-- response --> {json.dumps(response.json(), indent=2)}")

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

        return result

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
                        obj = {}
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
        query
        ---
        tag: validation
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
        self.validate (request)
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
        for i in message["knowledge_map"]:
            for n in i:
                for k in i[n]:
                    for enum, binding in enumerate(i[n][k]):
                        identifierSource = binding.split(":")
                        if identifierSource[0] == "CHEMBL.COMPOUND":
                            binding = "CHEMBL:"+identifierSource[1]
                        # print(element['curie'],curie)
                        i[n][k][enum] = binding
        for element in message["knowledge_graph"]["nodes"]:
            identifierSource = element["id"].split(":")
            if identifierSource[0] == "CHEMBL.COMPOUND":
                element["id"] = "CHEMBL:"+identifierSource[1]
        for element in message["knowledge_graph"]["edges"]:
            for prop in ["source_id","target_id"]:
                identifierSource = element[prop].split(":")
                if identifierSource[0] == "CHEMBL.COMPOUND":
                    element[prop] = "CHEMBL:"+identifierSource[1]
        return message
    def post(self):
        """
        Query RTX
        ---
        tag: validation
        description: Query Rtx, given a question graph.
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
        self.validate(request)

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
        return result

class IndigoQuery(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.base_url = 'https://indigo.ncats.io'
        self.query_url = f'{self.base_url}/reasoner/api/v1/query'
    def post(self):
        """
        Indigo Query
        ---
        tag: validation
        description: Query Indigo, given a question graph.
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
                            example: "Sucessfully validated"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string
        """
        self.validate(request)

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
            result = self.normalize_message(response.json())
        return result

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
        self.quick_url = f'{self.robokop_url}/api/simple/quick/?max_connectivity=1000'
    def view_url (self, uid):
        return f'{self.robokop_url}/simple/view/{uid}'

class GammaQuery(GammaResource):
    """ Generic graph query to Gamma. """
    def __init__(self):
        super().__init__()
    def post(self):
        """
        Visualize
        ---
        tag: validation
        description: Query Gamma, given a question graph.
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
        self.validate (request)
        result = {}
        del request.json['knowledge_graph']
        del request.json['knowledge_maps']
        del request.json['options']
        response = requests.post (self.quick_url, json=request.json)
        # print (f"{json.dumps(response.json (), indent=2)}")
        if response.status_code >= 300:
            result = {
                "status" : "error",
                "code"   : "service_invocation_failure",
                "message" : f"Bad Gamma quick response. url: {self.robokop_url} \n request: {json.dumps(request.json, indent=2)} response: \n{response.text}."
            }
        else:
            result = self.normalize_message (response.json ())
        return result

class PublishToGamma(GammaResource):
    """ Publish a graph to Gamma. """
    def __init__(self):
        super().__init__()
    def post(self):
        """
        Visualize
        ---
        tag: validation
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
        self.validate (request)
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
        tag: validation
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
        tag: validation
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
        self.validate (request)
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

# Workflow specific
api.add_resource(ICEESClusterQuery, '/clinical/cohort/disease_to_chemical_exposure')
api.add_resource(ICEESSchema, '/clincial/icees/schema')

# Visualization
api.add_resource(PublishToGamma, '/visualize/gamma')
api.add_resource(PublishToNDEx, '/visualize/ndex')

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
