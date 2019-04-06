"""
Provide a standard protocol for asking graph oriented questions of Translator data sources.
"""
import copy
import argparse
import json
import os
import yaml
import jsonschema
import requests
from flask import Flask, request, abort, Response
from flask_restful import Api, Resource
from flasgger import Swagger
from flask_cors import CORS
#from tranql.lib.ndex import NDEx
from tranql.main import TranQL
import networkx as nx
from tranql.util import JSONKit
from tranql.concept import BiolinkModelWalker
from tranql.backplane.iceesclient import ICEES

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
    def normalize_message (self, message):
        if 'answers' in message:
            message['knowledge_map'] = message['answers']
        return message

class TranQLQuery(StandardAPIResource):
    """ TranQL Resource. """

    def __init__(self):
        super().__init__()
        
    def post(self):
        """
        query
        ---
        tag: validation
        description: TranQL Query
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            query:
                                type: string
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
        #self.validate (request)
        tranql = TranQL ()
        print (request.json)
        query = request.json['query']
        print (f"----------> query: {query}")
        context = tranql.execute (query, cache=True)
        result = context.mem.get ('result', {})
        #print (result)
        return self.normalize_message (result)
    
class ICEESClusterQuery(StandardAPIResource):
    """ ICEES Resource. """

    def __init__(self):
        super().__init__()
        self.cluster_args = ICEESClusterArgs ()
        
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
        icees = ICEES ()
        correlation = None
        self.parse_options (request.json['options'])
        cohort_id = "COHORT:22" \
                    if self.cluster_args.cohort_id == 'all_patients' \
                    else self.cluster_args.cohort_id
        correlation = icees.feature_to_all_features (
            feature=self.cluster_args.feature_id,
            value=self.cluster_args.value,
            operator=self.cluster_args.operator,
            max_p_val=self.cluster_args.max_p_val,
            cohort_id=cohort_id)
        request.json['knowledge_graph'] = icees.parse_1_x_N (correlation)
        self.gen_cluster_answers (request.json)
        #print (json.dumps(request.json, indent=2))
        return self.normalize_message (request.json)

    def gen_cluster_answers (self, message):
        """ We probably want a more robust reasoner-like ability to answer 
        general questions. For now, write bindings specific to this question. """
        question = message['question_graph']
        question_nodes = question['nodes']
        question_edges = question['edges']        
        kg = message['knowledge_graph']
        nodes = kg['nodes']
        edges = kg['edges']
        message['answers'] = []
        bindings = message['answers']
        for node in nodes:
            """ Type must match icees response. 
            Change this when icees returns drug_exposure. """
            if node['type'] == 'chemical_substance': #'drug_exposure':
                #print (f"{json.dumps(question_nodes, indent=2)}")
                node_bindings = {
                    question_nodes[1]['id'] : node['id']
                }
                edge_bindings = [ e['id'] for e in edges if e['target_id'] == node['id'] ]
                bindings.append ({
                    "node_bindings" : node_bindings,
                    "edge_bindings" : edge_bindings
                })
        
    def parse_options (self, options):
        for k in options.keys ():
            if hasattr(self.cluster_args, k):
                setattr (self.cluster_args, k, options[k])
        feature = self.get_feature ()
        if feature in options:
            self.cluster_args.operator = options[feature][0]
            self.cluster_args.value = options[feature][1]
            
    def get_feature (self):
        return "EstResidentialDensity"
    
class ICEESEdVisitsClusterQuery(ICEESClusterQuery):
    """ ICEES Resource. """
    def __init__(self):
        super(ICEESClusterQuery, self).__init__()
        self.cluster_args = ICEESClusterArgs (
            cohort_id="COHORT:22",
            feature_id="TotalEDInpatientVisits",
            value="2",
            operator="<",
            max_p_val="0.1")
    def get_feature (self):
        return "TotalEDInpatientVisits"

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

#######################################################
##
## Gamma - publish a graph to Gamma.
##
#######################################################
class GammaResource(StandardAPIResource):
    def __init__(self):
        super().__init__()
        #self.robokop_url = 'http://robokopdb2.renci.org'
        self.robokop_url = 'http://robokop.renci.org'
        #self.robokop_url = 'http://robokop.renci.org'
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

        """ This is just a pass-through to simplify workflow syntax. """
        
        self.validate (request)
        #print (json.dumps(request.json, indent=2))
        response = requests.post (self.quick_url, json=request.json)
        if response.status_code >= 300:
            print(response)
            print(response.text)
            raise Exception("Bad Gamma quick response.")
        #print (json.dumps(response.json (), indent=2))
        return self.normalize_message (response.json ())

class RTXQuery(StandardAPIResource):
    """ Generic graph query to RTX. """
    def __init__(self):
        super().__init__()
    def post(self):
        """
        Visualize
        ---
        tag: validation
        description: Query RTX, given a question graph.
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

        """ This is just a pass-through to simplify workflow syntax. """
        
        self.validate (request)
        url = "https://rtx.ncats.io/beta/api/rtx/v1/query"
        #request.json['results'] = []
        del request.json['knowledge_graph']
        del request.json['knowledge_maps']
        del request.json['options']
        edges = request.json['question_graph']['edges']
        del edges[0]
        nodes = request.json['question_graph']['nodes']
        del nodes[0]
        query = {
            "bypass_cache": "true",
            "query_message" : {
                "query_graph" : request.json['question_graph']
            }
        }
        '''
            "previous_message_processing_plan" : {
                "previous_messages" : [
                    request.json
                ]
            }
        '''

        query = {
            "bypass_cache": "true",
            "query_message": {
                "query_graph": {
                    "edges": [
                        {
                            "edge_id": "e00",
                            "source_id": "n00",
                            "target_id": "n01",
                            "type": "physically_interacts_with"
                        }
                    ],
                    "nodes": [
                        {
                            "curie": "CHEMBL.COMPOUND:CHEMBL112",
                            "node_id": "n00",
                            "type": "chemical_substance"
                        },
                        {
                            "node_id": "n01",
                            "type": "protein"
                        }
                    ]
                }
            }
        }
        print (json.dumps(query, indent=2))
        response = requests.post (url, json=query)
        if response.status_code >= 300:
            print(response)
            print(response.text)
            raise Exception("Bad RTX query response.")
        print (json.dumps(response.json (), indent=2))
        return self.normalize_message (response.json ())

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
        print (f"{json.dumps(request.json, indent=2)}")
        view_post_response = requests.post(
            self.view_post_url,
            json=request.json)
        if view_post_response.status_code >= 300:
            print(f"{view_post_response}")
            raise Exception("Bad response view post")        
        uid = json.loads(view_post_response.text)
        print(f"view-post-response: {view_post_response}")
        print(f"view-url: {self.view_url(uid)}")

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

api.add_resource(TranQLQuery, '/graph/tranql')

# Generic
api.add_resource(GammaQuery, '/graph/gamma/quick')
api.add_resource(RTXQuery, '/graph/rtx/query')
api.add_resource(BiolinkModelWalkerService, '/implicit_conversion')

# Workflow specific
#api.add_resource(ICEESClusterQuery, '/flow/5/mod_1_4/icees/by_residential_density')
api.add_resource(ICEESClusterQuery, '/clinical/cohort/disease_to_chemical_exposure')
api.add_resource(ICEESEdVisitsClusterQuery, '/flow/5/mod_1_4/icees/by_ed_visits')

# Visualization
api.add_resource(PublishToGamma, '/visualize/gamma')
api.add_resource(PublishToNDEx, '/visualize/ndex')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='TranQL Backplane')
    parser.add_argument('-port', action="store", dest="port", default=8099, type=int)
    args = parser.parse_args()

    server_host = '0.0.0.0'
    server_port = args.port

    app.run(
        host=server_host,
        port=server_port,
        debug=False,
        use_reloader=True
    )

