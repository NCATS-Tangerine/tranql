from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource

#######################################################
##
#  NDEx - publish a graph to NDEx
##
#######################################################


class PublishToNDEx(StandardAPIResource):
    """ Publish a graph to NDEx. """
    def __init__(self):
        super().__init__()

    def post(self):
        """
        Publish a graph to NDEx
        ---
        tags: [publish]
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
        self.validate(request, 'Message')
        name = request.json.get('options', {}).get('name', None)
        if name is not None:
            ndex = NDEx()
            ndex.publish_graph(
                name=name,
                graph={
                    "nodes": request.json['knowledge_graph']['nodes'],
                    "edges": request.json['knowledge_graph']['edges']
                })

