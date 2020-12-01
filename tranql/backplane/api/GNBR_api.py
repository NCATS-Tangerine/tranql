import requests
from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource
import logging
from tranql.config import config

logger = logging.getLogger(__name__)


class GNBRReasoner:

    def query(self, message):
        url = config.get("GNBR_URL")
        response = requests.post(url, json=message)
        print(f"Return Status: {response.status_code}")
        result = {}
        if response.status_code == 200:
            result = response.json()
        return result


class GNBRDecorator(StandardAPIResource):
    """ GNBR Knowledge Graph annotator."""

    def post(self):
        """
        Decorate a knowledge graph via GNBR.
        ---
        tags: [query]
        description: GNBR decorator.
        requestBody:
            description: Input message
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
        """
        knowledge_graph = request.json['knowledge_graph']
        mapped_message = {
            'result_graph': {
                'edge_list': [],
                'node_list': []
            }
        }
        for edge in knowledge_graph['edges']:
            edge['publications'] = edge.get('publications', '')
            if isinstance(edge['publications'], list):
                edge['publications'] = ','.join(edge['publications'])
            mapped_message['result_graph']['edge_list'].append(edge)
        for node in knowledge_graph['nodes']:
            mapped_message['result_graph']['node_list'].append(node)
        rtx = {
            'result_list': [
                mapped_message
            ]
        }
        index = 0
        rtx_result = rtx['result_list'][index]
        for edge in rtx_result['result_graph']['edge_list']:
            edge['publications'] = edge.get('publications', [])
            if isinstance(edge['publications'], str):
                edge['publications'] = list(edge['publications'].split(','))
        for node in rtx_result['result_graph']['node_list']:
            if not isinstance(node['type'], list):
                node['type'] = [node['type']]
        node_list = rtx_result['result_graph']['node_list']
        edge_list = rtx_result['result_graph']['edge_list']

        gnbr_reasoner = GNBRReasoner()
        return gnbr_reasoner.query({
            "query_message": {
                "query_graph": {
                    'nodes': node_list,
                    'edges': edge_list
                }
            }
        })
