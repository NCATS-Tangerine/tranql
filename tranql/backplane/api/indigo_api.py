from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource
from tranql.config import config

class IndigoQuery(StandardAPIResource):
    def __init__(self):
        super().__init__()
        self.base_url = config.get("INDIGO_URL")
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
