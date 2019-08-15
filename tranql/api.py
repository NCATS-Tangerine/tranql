"""
Provide a standard protocol for asking graph oriented questions of Translator data sources.
"""
import copy
import argparse
import json
import logging
import os
import traceback
import yaml
import jsonschema
import requests
from flask import Flask, request, abort, Response, send_from_directory
from flask_restful import Api, Resource
from flasgger import Swagger
from flask_cors import CORS
from tranql.concept import ConceptModel
from tranql.main import TranQL, TranQLIncompleteParser
from tranql.tranql_ast import SelectStatement
import networkx as nx
from tranql.util import JSONKit
from tranql.tranql_schema import GraphTranslator, Schema
from tranql.concept import BiolinkModelWalker
from tranql.exception import TranQLException
#import flask_monitoringdashboard as dashboard

logger = logging.getLogger (__name__)

web_app_root = os.path.join (os.path.dirname (__file__), "..", "web", "build")

app = Flask(__name__, static_folder=web_app_root)
#dashboard.bind(app)

api = Api(app)
CORS(app)

app.config['SWAGGER'] = {
    'title': 'TranQL API',
    'description': 'Translator Query Language (TranQL) API',
    'uiversion': 3,
    'openapi': '3.0.1'
}
filename = 'translator_interchange.yaml'
filename = os.path.join (os.path.dirname(__file__), 'backplane', filename)

definitions_filename = 'definitions.yaml'
definitions_filename = os.path.join (os.path.dirname(__file__), definitions_filename)
with open(filename, 'r') as file_obj:
    template = {
        "definitions" : yaml.load(file_obj)["definitions"],
        "tags": [
            {"name" : "query"},
            {"name" : "schema"},
            {"name" : "util"},
            {"name" : "configuration"},
            {"name" : "webapp"}
        ]
    }
    with open(definitions_filename, 'r') as definitions_file:
        template['definitions'].update(yaml.load(definitions_file))
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

class StandardAPIResource(Resource):
    @staticmethod
    def validate (request):
        with open(filename, 'r') as file_obj:
            specs = yaml.load(file_obj)
        to_validate = specs["components"]["schemas"]["Message"]
        to_validate["components"] = specs["components"]
        to_validate["components"].pop("Message", None)
        try:
            jsonschema.validate(request.json, to_validate)
        except jsonschema.exceptions.ValidationError as error:
            logging.error (f"ERROR: {str(error)}")
            abort(Response(str(error), 400))
    @staticmethod
    def handle_exception (e, warning=False):
        result = {"errors": []}
        if isinstance (e, list):
            [result["errors"].extend(StandardAPIResource.handle_exception(exception)["errors"]) for exception in e]
        elif isinstance (e, TranQLException):
            result["errors"].append({
                "message" : str(e),
                "details" : str(e.details) if e.details else ''
            })
        elif isinstance (e, Exception):
            result["errors"].append({
                "message" : str(e),
                "details" : ''
            })
        elif isinstance (e, str):
            result["errors"].extend(StandardAPIResource.handle_exception(Exception(e))["errors"])

        traceback.print_exc ()

        if warning:
            result["status"] = "Warning"
        else:
            result["status"] = "Error"


        return result

    @staticmethod
    def response(data):
        status_code = 200
        if isinstance(data, dict):
            status = data.get('status',None)
            if status == "Error":
                status_code = 500
        return (data, status_code)
class WebAppRoot(Resource):
    def get(self):
        """
        Web app root
        ---
        tags: [webapp]
        consumes': [ 'text/plain' ]
        """
        return send_from_directory(web_app_root, 'index.html')
api.add_resource(WebAppRoot, '/', endpoint='webapp_root')

class WebAppPath(Resource):
    def get(self, path):
        """
        Web app path
        ---
        tags: [webapp]
        parameters:
            - in: path
              name: path
              schema:
                type: string
              required: true
              description: Resource path.
        """
        resource_path = os.path.join (os.path.dirname (__file__), os.path.sep, path)
        logger.debug (f"--path: {resource_path}")
        if path != "" and os.path.exists(web_app_root + "/" + path):
            return send_from_directory(web_app_root, path)
        else:
            abort (404)
api.add_resource(WebAppPath, '/<path:path>', endpoint='webapp_path')


class Configuration(StandardAPIResource):
    """ Configuration """
    def get(self):
        """
        TranQL Configuration
        ---
        tags: [configuration]
        description: TranQL Configuration
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                          type: object

        """
        return self.response({
            "api_url" : config['API_URL'],
            "robokop_url" : config['ROBOKOP_URL']
        })
class DecorateKG(StandardAPIResource):
    """ Exposes an endpoint that allows for the decoration of a KGS 0.1.0 knowledge graph with TranQL's decorate method. """
    def __init__(self):
        super().__init__()

    def post(self):
        """
        Decorate a Knowledge Graph
        ---
        tags: [util]
        description: Decorates a knowledge graph's elements with given data using TranQL's decorate method.
        requestBody:
          name: knowledge_graph
          description: A KGS 0.1.0 compliant KGraph
          required: true
          content:
            application/json:
             schema:
               $ref: '#/definitions/KGraph'
             example:
               nodes:
                 - id: n0
                   type: chemical_substance
                 - id: n1
                   type: gene
               edges:
                 - id: e0
                   type: targets
                   source_id: n0
                   target_id: n1
        parameters:
            - in: query
              name: reasoners
              schema:
                type: array
                items:
                  type: string
              example:
                - rtx
                - robokop
              required: false
              description: The reasoner that the knowledge graph originates from.
        responses:
            '200':
                description: Knowledge Graph
                content:
                    application/json:
                        schema:
                          $ref: '#/definitions/KGraph'
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                          $ref: '#/definitions/Error'
        """
        message = { "knowledge_graph" : request.json }
        reasoners = request.args.getlist('reasoners',None)

        options = {}

        if reasoners != None:
            options["schema"] = reasoners

        SelectStatement.decorate_result(message, options)

        return self.response(message["knowledge_graph"])
class MergeMessages(StandardAPIResource):
    """ Exposes an endpoint that allows for the merging of an arbitrary amount of messages """

    def __init__(self):
        super().__init__()

    def post(self):
        """
        Merge Messages
        ---
        tags: [util]
        description: Merge Message objects together using TranQL's merge_results method.
        requestBody:
          name: messages
          description: An array of KGS 0.1.0 compliant message objects
          required: true
          content:
            application/json:
             schema:
               type: array
               items:
                  $ref: '#/definitions/Message'
             example:
               - knowledge_graph:
                   nodes:
                     - id: TEST:CS1
                       type: chemical_substance
                     - id: TEST:G1
                       type: gene
                   edges:
                     - type: targets
                       source_id: TEST:CS1
                       target_id: TEST:G1
               - knowledge_graph:
                   nodes:
                     - id: TEST:merged
                       type:
                         - chemical_substance
                         - Drug
                       equivalent_identifiers:
                         - TEST:CS1
                     - id: TEST:CS2
                       type: chemical_substance
                     - id: TEST:G2
                       type: gene
                   edges:
                     - type: interacts_with
                       source_id: TEST:CS2
                       target_id: TEST:G2
        parameters:
            - in: query
              name: name_based_merging
              schema:
                type: boolean
                default: true
              required: false
              description: Tells the merger whether or not to merge elements with identical `name` properties.
            - in: query
              name: resolve_names
              schema:
                type: boolean
                default: false
              required: false
              description: >
                (Experimental) Tells the merger to invoke the Bionames API on nodes in order to get more equivalent identifiers.
                Ideally, this should result in a more thoroughly merged graph, as fewer equivalent nodes will fail to be detected.
                This currently should not be used on large queries (1000+ nodes), or it will end up flooding the Bionames API.
            - in: query
              name: question_graph
              schema:
                type: string
              description: The JSON serialized question graph that the result should retain
            - in: query
              name: root_order
              schema:
                type: array
                items:
                  type: string
              required: false
              description: >
                If merging messages with separate paths, e.g. population_of_individual_organisms->chemical_substance and chemical_substance->disease,
                the root order (["population_of_individual_organisms", "chemical_substance", "disease"]) of the two messages must be known in order to
                successfully merge their knowledge maps together. If every message has the same order, you don't care about their knowledge maps, or
                there is only one response, then this parameter is not required. If the parameter is not provided, then it will concatenate all each
                response's knowledge map.
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
        messages = request.json
        interpreter_options = {
            "name_based_merging" : request.args.get('name_based_merging','true').upper() == 'TRUE',
            "resolve_names" : request.args.get('resolve_names','false').upper() == 'TRUE'
        }
        root_question_graph = json.loads(request.args['question_graph'])
        root_order = request.args.get('root_order',None)
        if root_order != None:
            # werkzeug.ImmutableMultiDict.getlist doesn't allow for a default if the key isn't present,
            # so first check if its present, and, if so, get it as a list.
            root_order = request.args.getlist('root_order')
        tranql = TranQL (options=interpreter_options)
        return self.response(SelectStatement.merge_results(messages,tranql,root_question_graph,root_order))
class TranQLQuery(StandardAPIResource):
    """ TranQL Resource. """

    def __init__(self):
        super().__init__()

    def post(self):
        """
        Query TranQL
        ---
        tags: [query]
        description: Execute a TranQL query.
        requestBody:
          name: query
          description: A valid TranQL program
          required: true
          content:
            text/plain:
             schema:
               type: string
             example: >
               select chemical_substance->gene->disease
                 from \"/graph/gamma/quick\"
                where disease=\"asthma\"
        parameters:
            - in: query
              name: dynamic_id_resolution
              schema:
                type: boolean
              required: false
              default: false
              description: Specifies if dynamic id lookup of curies will be performed
            - in: query
              name: asynchronous
              schema:
                type: boolean
              required: false
              default: true
              description: Specifies if requests made by TranQL will be asynchronous.
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
        #self.validate (request)
        result = {}

        logging.debug (request.data)
        query = request.data.decode('utf-8')
        dynamic_id_resolution = request.args.get('dynamic_id_resolution','False').upper() == 'TRUE'
        asynchronous = request.args.get('asynchronous', 'True').upper() == 'TRUE'
        logging.debug (f"--> query: {query}")
        tranql = TranQL (options = {
            "dynamic_id_resolution" : dynamic_id_resolution,
            "asynchronous" : asynchronous
        })
        try:
            context = tranql.execute (query) #, cache=True)
            result = context.mem.get ('result', {})
            logger.debug (f" -- backplane: {context.mem.get('backplane', '')}")
            if len(context.mem.get ('requestErrors', [])) > 0:
                errors = self.handle_exception(context.mem['requestErrors'], warning=True)
                result.update(errors)
        except Exception as e:
            traceback.print_exc()
            errors = [e, *tranql.context.mem.get ('requestErrors', [])]
            result = self.handle_exception (errors)
        with open ('query.out', 'w') as stream:
            json.dump (result, stream, indent=2)

        return self.response(result)

class AnnotateGraph(StandardAPIResource):
    """ Request the message object to be annotated by the backplane and return the annotated message """

    def __init__(self):
        super().__init__()

    def post(self):
        """
        Annotate Graph
        ---
        tags: [query]
        description: Annotate a message's knowledge graph via the GNBR decorator.
        requestBody:
          name: message
          description: A KGS 0.1.0 compliant Message
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
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                          $ref: '#/definitions/Error'
        """
        tranql = TranQL ()
        messageObject = request.json
        url = tranql.context.mem.get('backplane') + '/graph/gnbr/decorate'

        logger.info(url)

        resp = requests.post(
            url = url,
            json = messageObject,
            headers = {
                'accept': 'text/plain'
            }
        )

        data = resp.json()

        for result in data['results']:
            type = result['result_type']
            if type in messageObject:
                messageObject[type] = result['result_graph']

        return self.response(messageObject)

class SchemaGraph(StandardAPIResource):
    """ Graph of schema to display to the client """

    def __init__(self):
        super().__init__()

    def get(self):
        """
        TranQL Schema
        ---
        tags: [schema]
        description: Get TranQL's schema.
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
        tranql = TranQL ()
        schema = Schema (backplane=tranql.context.mem.get('backplane'))
        schemaGraph = GraphTranslator(schema.schema_graph)

        # logger.info(schema.schema_graph.net.nodes)
        # logger.info(schemaGraph.graph_to_message())

        # return {"nodes":[],"links":[]}
        obj = {
            "schema": schemaGraph.graph_to_message(),
        }
        if len(schema.loadErrors) > 0:
            errors = self.handle_exception(schema.loadErrors, warning=True)
            for key in errors:
                obj[key] = errors[key]
        return self.response(obj)

class ModelConceptsQuery(StandardAPIResource):
    """ Query model concepts. """

    def __init__(self):
        super().__init__()

    def post(self):
        """
        Biolink Model Concepts
        ---
        tags: [schema]
        description: Get valid concepts in the biolink model.
        responses:
            '200':
                description: Array of concepts
                content:
                    application/json:
                        schema:
                          type: array
                          items:
                            type: string

        """
        result = {}
        try:
            concept_model = ConceptModel ("biolink-model")
            result = sorted (list(concept_model.by_name.keys ()))
            logging.debug (result)
        except Exception as e:
            #traceback.print_exc (e)
            result = self.handle_exception (e)
        return self.response(result)


class ModelRelationsQuery(StandardAPIResource):
    """ Query model relations. """

    def __init__(self):
        super().__init__()

    def post(self):
        """
        Biolink Model Relations
        ---
        tags: [schema]
        description: Get valid relations in the biolink model.
        responses:
            '200':
                description: Array of relations
                content:
                    application/json:
                        schema:
                          type: array
                          items:
                            type: string

        """
        result = {}
        try:
            concept_model = ConceptModel ("biolink-model")
            result = sorted (list(concept_model.relations_by_name.keys ()))
            logging.debug (result)
        except Exception as e:
            #traceback.print_exc (e)
            result = self.handle_exception (e)
        return self.response(result)

class ReasonerURLs(StandardAPIResource):
    """ Returns the URLs corresponding to `reasoner` properties. """
    def __init__(self):
        super().__init__()

    def get(self):
        """
        Retrieve Reasoner URLs
        ---
        tags: [util]
        description: Returns the corresponding schema URLs of each `reasoner` value.
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                          type: object
        """
        tranql = TranQL ()
        schema = Schema (backplane=tranql.context.mem.get('backplane'))

        return { schema[0] : schema[1]['url'] for schema in schema.schema.items() }

class ParseIncomplete(StandardAPIResource):
    """ Tokenizes an incomplete query and returns the result """
    def __init__(self):
        super().__init__()

    def parse(self, parser, query):
        if isinstance(query, str):
            parsed = parser.tokenize (query)
            result = parsed.asList ()
        else:
            result = [self.parse(parser, q) for q in query]
        return result
    def post(self):
        """
        Parse Incomplete Query
        ---
        tags: [util]
        description: Tokenizes an incomplete query and returns the result
        requestBody:
          name: query
          description: A TranQL program
          content:
            text/plain:
              schema:
                type: string
              examples:
                Concept:
                  value: select chemical_substance->
                  summary: No concept provided
                Partial_concept:
                  value: select chemical_substance->dis
                  summary: Concept partially completed
                Predicate:
                  value: select chemical_substance-[
                  summary: No predicate provided
                Partial_predicate:
                  value: select chemical_substance-[direc
                  summary: Predicate partially completed
                Nothing:
                  value: select
                  summary: Nothing provided
            application/json:
              schema:
                type: array
                items:
                  type: string
              examples:
                Partial query:
                  value:
                    - select chemical_substance-[
                    - select chemical_substance-[]->gene
                  summary: Partial query
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                          type: array
                        example:
                          -  -  - "select"
                                - "chemical_substance"
                                -  - "-["
                                   - "predicate"
                                   - "]->"
                                - "incomplete_con"
                             - []
                             -  - ""
                             -  - ""
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                          $ref: '#/definitions/Error'
        """
        if request.content_type == "text/plain":
            query = request.data.decode('utf-8')
        else:
            query = request.json

        tranql = TranQL ()
        parser = TranQLIncompleteParser (tranql.context.resolve_arg ("$backplane"))

        result = None

        try:
            result = self.parse(parser, query)

        except Exception as e:
            result = self.handle_exception(e)
        return self.response(result)

###############################################################################################
#
# Define routes.
#
###############################################################################################

api.add_resource(TranQLQuery, '/tranql/query')
api.add_resource(SchemaGraph, '/tranql/schema')
api.add_resource(AnnotateGraph, '/tranql/annotate')
api.add_resource(MergeMessages,'/tranql/merge_messages')
api.add_resource(DecorateKG,'/tranql/decorate_kg')
api.add_resource(ModelConceptsQuery, '/tranql/model/concepts')
api.add_resource(ModelRelationsQuery, '/tranql/model/relations')
api.add_resource(ParseIncomplete, '/tranql/parse_incomplete')
api.add_resource(ReasonerURLs, '/tranql/reasonerURLs')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Short sample app')
    parser.add_argument('--host', action="store", dest="host", default='0.0.0.0')
    parser.add_argument('--port', action="store", dest="port", default=8001, type=int)
    parser.add_argument('-d', '--debug', help="Debug log level.", default=False, action='store_true')
    parser.add_argument('-r', '--reloader', help="Use reloader independent of debug.", default=False, action='store_true')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=args.debug or args.reloader
    )
