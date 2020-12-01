import requests
import json
from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource
from tranql.config import config


class RtxSchema(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.base_url = config.get("RTX_URL")
        self.predicates_url = self.base_url + '/beta/api/rtx/v1/predicates'

    def get(self):
        """
        RTX schema
        ---
        tags: [schema]
        description: Query the RTX reasoner.
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
        response = requests.get(self.predicates_url)
        if response.status_code != 200:
            result = {
                "status": "error",
                "code": "service_invocation_error",
                "message": f"Bad RTX response. When getting schema. url: {self.predicates_url} \n request: "
                f"{json.dumps(request.json, indent=2)} "
                f"response: \n{response.text}."
            }
            return result, 500
        else:
            return response.json()


class RtxQuery(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.base_url = config.get("RTX_URL")
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
                    "status": "error",
                    "code": "service_invocation_failure",
                    "message": f"Bad Rtx query response. url: {self.query_url} \n request: {json.dumps(data, indent=2)} \nresponse: \n{response.text}\n (code={response.status_code})."
                }
        else:
            result = self.convert_curies_to_standard(self.normalize_message(response.json()))
        return self.response(result)