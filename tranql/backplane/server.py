"""
Provide a standard protocol for asking graph oriented questions of Translator data sources.
"""

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
from tranql.lib.ndex import NDEx
import networkx as nx
from ndex2 import create_nice_cx_from_networkx
from ndex2.client import Ndex2
from tranql.util import JSONKit

from iceesclient import ICEES

app = Flask(__name__)

api = Api(app)
CORS(app)

""" https://github.com/NCATS-Gamma/NCATS-ReasonerStdAPI """
filename = 'translator_interchange.yaml'
filename = 'translator_interchange_0.9.0.yaml'
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
    
class ICEESClusterQuery(StandardAPIResource):
    """ ICEES Resource. """

    def __init__(self):
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
        #print (json.dumps(request.json, indent=2))
        return request.json

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
        #self.robokop_url = 'http://robokopdb2.renci.org'
        self.robokop_url = 'http://robokop.renci.org'
        #self.robokop_url = 'http://robokop.renci.org'
        self.view_post_url = f'{self.robokop_url}/api/simple/view/'
        self.quick_url = f'{self.robokop_url}/api/simple/quick/?max_connectivity=1000'
    def view_url (self, uid):
        return f'{self.robokop_url}/simple/view/{uid}'

class GammaQuery(GammaResource):
    """ Generic graph query to Gamma. """
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
        print (json.dumps(request.json, indent=2))
        response = requests.post (self.quick_url, json=request.json)
        if response.status_code >= 300:
            print(response)
            print(response.text)
            raise Exception("Bad Gamma quick response.")
        print (json.dumps(response.json (), indent=2))
        return response.json ()
        
class PublishToGamma(GammaResource):
    """ Publish a graph to Gamma. """
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

###############################################################################################
#
# Define routes.
#
###############################################################################################

# Generic
api.add_resource(GammaQuery, '/graph/gamma/quick')

# Workflow specific
#api.add_resource(ICEESClusterQuery, '/flow/5/mod_1_4/icees/by_residential_density')
api.add_resource(ICEESClusterQuery, '/clinical/cohort/disease_to_chemical_exposure')
api.add_resource(ICEESEdVisitsClusterQuery, '/flow/5/mod_1_4/icees/by_ed_visits')

# Visualization
api.add_resource(PublishToGamma, '/visualize/gamma')
api.add_resource(PublishToNDEx, '/visualize/ndex')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Short sample app')
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
