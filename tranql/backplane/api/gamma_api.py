import requests
import json
from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource
import logging
from tranql.config import config

logger = logging.getLogger(__name__)

#######################################################
##
#  Gamma - publish a graph to Gamma.
##
#######################################################


class GammaResource(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.robokop_url = config.get("GAMMA_URL")
        self.view_post_url = f'{self.robokop_url}/api/simple/view/'
        self.quick_url = f'{self.robokop_url}/api/simple/quick/?rebuild=false&output_format=MESSAGE&max_connectivity=0&max_results=300'

    def view_url(self, uid):
        return f'{self.robokop_url}/simple/view/{uid}'


class GammaSchema(GammaResource):
    def __init__(self):
        super().__init__()

    def get(self):
        """Robokop schema
        ---
        tags: [schema]
        description: Meta graph of the Robokop reasoner.
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            source_type:
                                target_type:
                                  - relation_1
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'
        """
        response = requests.get(self.robokop_url + '/api/predicates', verify=False)
        if response.status_code >= 300:
            result = {
                "status": "error",
                "code": "service_invocation_failure",
                "message": f"Bad Gamma quick response schema. url: {self.robokop_url} \n request: {json.dumps(request.json, indent=2)} response: \n{response.text}."
            }
        else:
            result = response.json()
        return self.response(result)


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
        self.validate(request, 'Message')
        result = {}
        del request.json['knowledge_graph']
        del request.json['knowledge_maps']
        del request.json['options']
        logger.debug(f"Making request to {self.quick_url}")
        logger.debug(json.dumps(request.json, indent=2))
        response = requests.post(self.quick_url, json=request.json, verify=False)
        if response.status_code >= 300:
            result = {
                "status": "error",
                "code": "service_invocation_failure",
                "message": f"Bad Gamma quick response. url: {self.robokop_url} \n request: {json.dumps(request.json, indent=2)} response: \n{response.text}."
            }
        else:
            result = self.normalize_message(response.json())
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
        self.validate(request, 'Message')
        if 'knowledge_map' in request.json:
            request.json['answers'] = request.json['knowledge_map']
            del request.json['knowledge_map']
        view_post_response = requests.post(
            self.view_post_url,
            json=request.json)
        if view_post_response.status_code >= 300:
            print(f"{view_post_response}")
            raise Exception("Bad response view post")
        uid = json.loads(view_post_response.text)
        print(f"view-post-response: {view_post_response}")
        print(f"view-url: {self.view_url(uid)}")
