import copy
import json
from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource
from tranql.concept import BiolinkModelWalker
import logging

logger = logging.getLogger(__name__)


class BiolinkModelWalkerService(StandardAPIResource):
    """ Biolink Model Walk Resource. """
    def __init__(self):
        super().__init__()

    def post(self):
        """
        biolink-model conversions.
        ---
        tags: [query]
        description: Convert biolink model types.
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
        self.validate(request, 'Message')
        question = request.json['question_graph']
        question_nodes = question['nodes']
        source_node = question_nodes[0]
        target_node = question_nodes[1]
        target_type = target_node['type']
        response = copy.deepcopy(request.json)
        if len(question_nodes) == 2:
            biolink_model_walker = BiolinkModelWalker()
            conversion = biolink_model_walker.translate(
                node=source_node,
                target_type=target_type)
            if conversion is not None:
                response['knowledge_graph'] = {
                    "nodes": [conversion],
                    "edges": []
                }
                response['answers'] = [
                    {
                        'node_bindings': {
                            target_type: conversion['id']
                        }
                    }
                ]
            else:
                raise ValueError(f"Unable to convert {source_node} to {target_type}")
            logger.debug(f" " + json.dumps(response, indent=2))
        if 'answers' not in response:
            response['answers'] = []
        return self.normalize_message(response)
