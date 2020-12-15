"""
Provide a normalized protocol for asking graph oriented questions of Translator data sources.
"""
import argparse
import json
import logging
import os
import yaml
import requests
from flask import Flask, request, Response, jsonify
from flask_restful import Api, Resource, abort
from flasgger import Swagger
from flask_cors import CORS
from tranql.backplane.api.standard_api import StandardAPIResource
from tranql.backplane.api.automat_api import AutomatQuery, AutomatSchema, AutomatRegistry
from tranql.backplane.api.gamma_api import GammaSchema, GammaQuery, PublishToGamma
from tranql.backplane.api.icees_api import ICEESClusterQuery, ICEESSchema
from tranql.backplane.api.biolink_walker_api import BiolinkModelWalkerService
from tranql.backplane.api.GNBR_api import GNBRDecorator
from tranql.backplane.api.NDEX_api import PublishToNDEx
from tranql.backplane.api.indigo_api import IndigoQuery
from tranql.backplane.api.rtx_query import RtxQuery, RtxSchema
from tranql.backplane.api.roger_api import RogerQuery, RogerSchema

logger = logging.getLogger(__name__)

app = Flask(__name__)

api = Api(app)
CORS(app)

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
    'description': 'Common inteface for several translator apis',
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

###############################################################################################
#
# Define routes.
#
###############################################################################################

# Generic
api.add_resource(GammaQuery, '/graph/gamma/quick')
api.add_resource(GammaSchema, '/graph/gamma/predicates')
api.add_resource(BiolinkModelWalkerService, '/implicit_conversion')
api.add_resource(GNBRDecorator, '/graph/gnbr/decorate')
api.add_resource(IndigoQuery, '/graph/indigo')
api.add_resource(RtxQuery, '/graph/rtx')
api.add_resource(RtxSchema, '/graph/rtx/predicates')
api.add_resource(AutomatQuery, '/graph/automat/<kp_tag>')
api.add_resource(AutomatSchema, '/graph/automat/<kp_tag>/predicates')
api.add_resource(AutomatRegistry, '/graph/automat/registry')
api.add_resource(RogerSchema, '/graph/roger/predicates')
api.add_resource(RogerQuery, '/graph/roger')

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
