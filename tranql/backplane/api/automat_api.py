import copy
import json
import requests
from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource
from tranql.config import config

#######################################################
##
# Automat - query Automat-KPs.
##
#######################################################


class AutomatResource(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.url = config.get("AUTOMAT_URL")

    def get_kp_reasoner_api(self, kp_tag):
        return f'{self.url}/{kp_tag}/query'

    def get_kp_schema_api(self, kp_tag):
        return f'{self.url}/{kp_tag}/predicates'


class AutomatSchema(AutomatResource):
    def __init__(self):
        super().__init__()

    def get(self, kp_tag):
        """
        Automat Schema
        ---
        tags: [schema]
        description: Query schema of kp in automat
        parameters:
            - in: path
              name: kp_tag
              schema:
                type: string
                example: uberon
              required: true
              description: KP identifier to get data from.
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
                            $ref: '#/definitions/Error'"""
        url = self.get_kp_schema_api(kp_tag)
        response = requests.get(url)
        if response.status_code != 200 :
            result = {
                "status": "error",
                "code": "service_invocation_error",
                "message": f"Bad Automat response. When getting schema. url: {self.url} \n request: {json.dumps(request.json, indent=2)} "
                f"response: \n{response.text}."
            }
            return result, 500
        else:
            return response.json()


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
        # question_graph should be query graph
        question = request.json
        question['query_graph'] = copy.deepcopy(question['question_graph'])
        del question['question_graph']
        del question['knowledge_graph']
        del question['knowledge_maps']

        response = requests.post(url, json={"message": question})
        if response.status_code >= 300:
            result = {
                "status": "error",
                "code": "service_invocation_failure",
                "message": f"Bad Automat response. url: {self.url} \n request: "
                f"{json.dumps(request.json, indent=2)} response: \n{response.text}."
            }
        else:
            result = self.down_cast_message(response.json())
        return self.response(result)


class AutomatRegistry(AutomatResource):

    def __init__(self):
        super().__init__()

    def get(self):
        """
                Automat query
                ---
                tags: [query]
                description: Query the Automat KPs.
                responses:
                    '200':
                        description: Message
                        content:
                            application/json:
                                schema:
                                    - 'intact'
                                    - 'ctd'
                    '500':
                        description: An error was encountered
                        content:
                            application/json:
                                schema:
                                    $ref: '#/definitions/Error'
        """
        response = requests.get(self.url + '/registry')
        if response.status_code == 200:
            return response.json()
        else:
            result = {
                "status": "error",
                "code": "service_invocation_failure",
                "message": f"Bad Automat response. Contacting registry url: {self.url} \n request: "
                f"{json.dumps(request.json, indent=2)} response: \n{response.text}."
            }
            return result

