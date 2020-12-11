import copy
import json
import requests
from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource
from tranql.config import config

#######################################################
##
# Roger - query Roger-KP.
##
#######################################################


class RogerResource(StandardAPIResource):
    def __init__(self):
        super().__init__()

        self.url = config.get('ROGER_URL')

    def get_kp_reasoner_api(self):
        return f'{self.url}/query'

    def get_kp_schema_api(self):
        return f'{self.url}/predicates'


class RogerSchema(RogerResource):
    def __init__(self):
        super().__init__()

    def get(self):
        """
        Automat Schema
        ---
        tags: [schema]
        description: Query schema of Roger
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
        url = self.get_kp_schema_api()
        response = requests.get(url, verify=False)
        if response.status_code != 200:
            result = {
                "status": "error",
                "code": "service_invocation_error",
                "message": f"Bad Automat response. When getting schema. url: {self.url} \n request: {json.dumps(request.json, indent=2)} "
                f"response: \n{response.text}."
            }
            return result, 500
        else:
            return response.json()


class RogerQuery(RogerResource):
    """ Generic graph query to Gamma. """
    def __init__(self):
        super().__init__()

    def post(self):
        """
        Automat query
        ---
        tags: [query]
        description: Query the Roger Kp.
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
        url = self.get_kp_reasoner_api()
        # question_graph should be query graph
        question = request.json
        question['query_graph'] = copy.deepcopy(question['question_graph'])
        del question['question_graph']
        del question['knowledge_graph']
        del question['knowledge_maps']

        response = requests.post(url, json={"message": question}, verify=False)
        if response.status_code >= 300:
            result = {
                "status": "error",
                "code": "service_invocation_failure",
                "message": f"Bad Roger response. url: {self.url} \n request: "
                f"{json.dumps(request.json, indent=2)} response: \n{response.text}."
            }
        else:
            result = self.down_cast_message(response.json())
        return self.response(result)
