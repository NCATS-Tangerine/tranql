###
# This merge strategy was adapted from strider (https://github.com/ranking-agent/strider)
####
from collections import defaultdict
import json, hashlib
from bmt import Toolkit
from functools import reduce
import copy


QUESTION_GRAPH_KEY = 'query_graph'
KNOWLEDGE_GRAPH_KEY = 'knowledge_graph'
KNOWLEDGE_MAP_KEY = 'results'

BL_VERSION = "1.6.1"
toolkit = Toolkit(schema=f"https://raw.githubusercontent.com/biolink/biolink-model/{BL_VERSION}/biolink-model.yaml")



def connect_knowledge_maps(responses):
    # each answer is a subset path defined by query_order
    # task here is
    # given a->b->c (query_order ) merge a->b from response-1 to b->c in response-2 where b is the same
    new_knowledge_map = []
    # STEP 1 some prep work , transforming knowledge map from every response,
    # getting the q_graph edges as a map for navigating through out knowledge_map
    # first lets get everything from all the responses into a giant list

    # 1.1 When SelectStatement generates question it uses same edge id for the query graph for different parts.
    # which would collisions here.

    all_knowledge_maps = reduce(lambda a, b: a + b,
                                map(lambda response: response.get(KNOWLEDGE_MAP_KEY, []), responses),
                                [])

    # transform q_graph_edges to
    # source : target : edge
    transformed_q_graph_edges = {}
    for r in responses:
        q_graph_edges = r[QUESTION_GRAPH_KEY]['edges']
        for edge_id, edge_attributes in q_graph_edges.items():
            transformed_q_graph_edges[edge_attributes['subject']] = transformed_q_graph_edges.get(edge_attributes['subject'], {})
            transformed_q_graph_edges[edge_attributes['subject']][edge_attributes['object']] = transformed_q_graph_edges[edge_attributes['subject']]\
                .get(edge_attributes['object'], set())
            transformed_q_graph_edges[edge_attributes['subject']][edge_attributes['object']].add(edge_id)
        # convert node ids into list, collect score aswell
    score_table = {}
    for bindings in all_knowledge_maps:
        score_key = set()
        nodes = bindings.get('node_bindings', {})
        edges = bindings.get('edge_bindings', {})
        score = bindings.get('score', 0)
        # Do this if binding has a score else it should be 0
        if score != 0:
            # convert nodes to list
            for concept in nodes:
                curie = reduce(lambda a, b: a + [b['id']], nodes[concept], [])
                for c in curie:
                    score_key.add(c)
            for edge_id in edges:
                edges_kg_ids = reduce(lambda a, b: a + [b['id']], edges[edge_id], [])
                for i in edges_kg_ids:
                    score_key.add(i)
        score_key = frozenset(score_key)
        score_table[score_key] = score

    # Step 2
    # make a transformed graph in a structure that makes it easier to extract the parts for final merged results
    # bindings.
    knowledge_map_graph_repr = {
        # frozenset(node_kg_id, node_q_id): [
            # (other_node_kg_id, other_node_q_id), (edge_kg_id, edge_q_id)
    #]
    }
    for answer in all_knowledge_maps:
        node_bindings = answer.get('node_bindings', {})
        edge_bindings = answer.get('edge_bindings', [])
        # first thing is let's find out potential source nodes
        # remember the transformed_q_graph_edges , we are going to use that here as our meta map
        freeze = lambda node_type, node_curie: frozenset({node_type, frozenset([n['id'] for n in node_curie])})
        for concept in node_bindings:
            is_source = concept in transformed_q_graph_edges
            if is_source:
                target_concepts = transformed_q_graph_edges[concept]
                # This would  be something like frozenset(curie, type)
                source_node_key = freeze(node_type=concept, node_curie=node_bindings[concept])
                # collected target nodes edges
                target_bindings_dict = knowledge_map_graph_repr.get(source_node_key, {})
                for target_concept in target_concepts:
                    # grab a target instance from node bindings
                    target_curie = node_bindings.get(target_concept, None)
                    if target_curie:
                        target_node_key = freeze(node_type=target_concept, node_curie=node_bindings[target_concept])
                        edges = []
                        # collect the edge(s), using the query graph edge id
                        edge_q_ids = transformed_q_graph_edges[concept][target_concept]
                        for edge_q_id in edge_q_ids:
                            if edge_q_id in edge_bindings:
                                edges.append({
                                    edge_q_id: edge_bindings[edge_q_id]
                                })
                        # If there are edges add them.
                        if edges:
                            target_bindings_dict[target_node_key] = target_bindings_dict.get(target_node_key, [])
                            target_bindings_dict[target_node_key] += edges
                knowledge_map_graph_repr[source_node_key] = target_bindings_dict

    # Using depth first search extract possible paths
    # from knowledge_map_graph_repr
    paths = []
    all_visits = set()
    for node in knowledge_map_graph_repr:
        visited = set()
        if node not in all_visits and knowledge_map_graph_repr[node]:
            find_all_paths(graph=knowledge_map_graph_repr, start=node,edge=None, visited=visited, stack=[], paths=paths)
            # mark all items in paths as visited so we don't start form them and have partial duplicates
            visited = set(map (lambda pair: pair[0], reduce(lambda accu, path: path + accu, paths , [])))
            all_visits.update(visited)


    merged_answers = []
    if len(paths) == 0:
        return [{"node_bindings": [], "edge_bindings": []}]
    for path in paths:
        answer = {
            'node_bindings': {},
            'edge_bindings': {}
        }
        for node_data, edge_data in path:
            node_0, node_1 = node_data
            # sometimes for the frozenset data structure the order gets messed up so checking for string
            node_q_id, node_kg_id = [node_0, node_1] if isinstance(node_0, str) else [node_1, node_0]

            answer['node_bindings'][node_q_id] = [{"id": curie} for curie in list(node_kg_id)]
            # Edge data contains information about incoming edge not out going so start nodes don't have any.
            if edge_data:
                for e in edge_data:
                    answer['edge_bindings'].update(e)
            answer['score'] = 0 # default score is 0
        merged_answers.append(answer)
    # answer_sets
    overlay_score(merged_answers, score_table)
    return merged_answers


def overlay_score(merged_answers, score_table):
    for score_key in score_table:
        if score_table[score_key] == 0:
            continue
        for answer in merged_answers:
            node_bindings = list(map(lambda x: answer['node_bindings'][x][0], answer['node_bindings']))
            edge_bindings = list(map(lambda x: answer['edge_bindings'][x][0], answer['edge_bindings']))
            # make sure score key contains all nodes
            nb_kg_ids = [x['id'] for x in  node_bindings]
            eb_kg_ids = [x['id'] for x in edge_bindings]
            filterd = list(filter(lambda x: x not in nb_kg_ids, score_key))
            # make sure edges are also contained
            filterd = list(filter(lambda x: x not in eb_kg_ids, filterd))
            # if 'filterd' is empty means this answer contains all the edges and nodes so will give it that score
            # @TODO maybe have score be a asscoiated with sets of nodes, so it perseves origninal meaning that the
            # @TODO kp intented
            if len(filterd) == 0:
                answer['score'] = score_table[score_key]


def find_all_paths(graph, start, edge, visited = set(),stack= [], paths=[]):
    stack.append([start, edge])
    visited.add(start)
    if start not in graph or not bool(len(graph[start])):
        paths.append(copy.deepcopy(stack))
        stack.pop(len(stack) - 1)
        visited.remove(start)
        return
    for node in graph[start]:
        if node not in visited:
            find_all_paths(graph, node, graph[start][node], visited, stack, paths)
    # remove the item from stack once its loop through
    if len(stack):
        node, edge = stack.pop(len(stack) - 1)
        visited.remove(node)


def find_biolink_leaves(biolink_concepts: list):
    """
    Given a list of biolink concepts, returns the leaves removing any parent concepts.
    :param biolink_concepts: list of biolink concepts
    :return: leave concepts.
    """
    ancestry_set = set()
    all_concepts = set(biolink_concepts)
    for x in all_concepts:
        ancestors = set(toolkit.get_ancestors(x, reflexive=False, formatted=True))
        ancestry_set = ancestry_set.union(ancestors)
    leaf_set = all_concepts - ancestry_set
    return list(leaf_set)

def deduplicate_by(elements, fcn):
    """De-duplicate list via a function of each element."""
    return list(dict((fcn(element), element) for element in elements).values())


def get_from_all(
    dictionaries,
    key,
    default=None
):
    """
    Get list of values from dictionaries.
    If it is not present in any dictionary, return the default value.
    """
    values = [d[key] for d in dictionaries if key in d]
    if len(values) > 0:
        return values
    else:
        return default


def filter_none(values):
    """ Filter out None values from list """
    return [v for v in values if v is not None]


def merge_listify(values):
    """
    Merge values by converting them to lists
    and concatenating them.
    """
    output = []
    for value in values:
        if isinstance(value, list):
            output.extend(value)
        else:
            output.append(value)
    return output


def all_equal(values: list):
    """ Check that all values in given list are equal """
    return all(values[0] == v for v in values)


def result_hash(result):
    """
    Given a results object, generate a hashable value that
    can be used for comparison.
    """
    node_bindings_information = frozenset(
        (key, frozenset(bound["id"] for bound in value))
        for key, value in result["node_bindings"].items()
    )
    edge_bindings_information = frozenset(
        (key, frozenset(bound["id"] for bound in value))
        for key, value in result["edge_bindings"].items()
    )
    return (node_bindings_information, edge_bindings_information)


def merge_edges(kedges):
    """ Smart merge function for KEdges """
    output_kedge = {}

    attributes_values = get_from_all(kedges, "attributes")
    if attributes_values:
        output_kedge["attributes"] = \
            deduplicate_by(
                filter_none(merge_listify(attributes_values)),
                lambda d: json.dumps(d, sort_keys=True))

    predicate_values = get_from_all(kedges, "predicate")
    if not all_equal(predicate_values):
        raise ValueError("Unable to merge edges with non matching predicates")
    output_kedge["predicate"] = predicate_values[0]

    subject_values = get_from_all(kedges, "subject")
    if not all_equal(subject_values):
        raise ValueError("Unable to merge edges with non matching subjects")
    output_kedge["subject"] = subject_values[0]

    object_values = get_from_all(kedges, "object")
    if not all_equal(object_values):
        raise ValueError("Unable to merge edges with non matching objects")
    output_kedge["object"] = object_values[0]

    return output_kedge

def deduplicate(values: list):
    """ Simple deduplicate that uses python sets """
    new_list = []
    for v in values:
        if v not in new_list:
            new_list.append(v)
    return new_list


def build_unique_kg_edge_ids(message):
    """
    Replace KG edge IDs with a string that represents
    whether the edge can be merged with other edges
    """

    # Make a copy of the edge keys because we're about to change them
    for edge_id in list(message["knowledge_graph"]["edges"].keys()):
        edge = message["knowledge_graph"]["edges"].pop(edge_id)
        new_edge_id_string = f"{edge['subject']}-{edge['predicate']}-{edge['object']}"

        # Build hash from ID string
        new_edge_id = hashlib.blake2b(
            new_edge_id_string.encode(),
            digest_size=6,
        ).hexdigest()

        # Update knowledge graph
        message["knowledge_graph"]["edges"][new_edge_id] = edge

        # Update results
        for result in message["results"]:
            for edge_binding_list in result["edge_bindings"].values():
                for eb in edge_binding_list:
                    if eb["id"] == edge_id:
                        eb["id"] = new_edge_id


def merge_nodes(knodes):
    """ Smart merge function for KNodes """
    output_knode = {}

    # We don't really know how to merge names
    # so we just pick the first we are given
    name_values = get_from_all(knodes, "name")
    if name_values:
        output_knode["name"] = name_values[0]

    category_values = get_from_all(knodes, "category") or get_from_all(knodes, "categories")
    if category_values:
        output_knode["category"] = \
            deduplicate(merge_listify(category_values))
        # make leaves come first
        leaves = set(find_biolink_leaves(output_knode["category"]))
        other_category = set(output_knode["category"]) - leaves
        output_knode["category"] = list(leaves) + list(other_category)

    attributes_values = get_from_all(knodes, "attributes")
    if attributes_values:
        output_knode["attributes"] = \
            deduplicate_by(
                filter_none(merge_listify(attributes_values)),
                lambda d: json.dumps(d, sort_keys=True))

    return output_knode


def merge_kgraphs(kgraphs):
    """ Merge knowledge graphs. """

    knodes = [kgraph["nodes"] for kgraph in kgraphs]
    kedges = [kgraph["edges"] for kgraph in kgraphs]

    # Merge Nodes
    output = {"nodes": {}, "edges": {}}

    all_node_keys = set()
    for kgraph in kgraphs:
        all_node_keys.update(kgraph["nodes"].keys())
    for node_key in all_node_keys:
        node_values = get_from_all(knodes, node_key)
        merged_node = merge_nodes(node_values)
        output["nodes"][node_key] = merged_node

    # Merge Edges
    all_edge_keys = set()
    for kgraph in kgraphs:
        all_edge_keys.update(kgraph["edges"].keys())
    for edge_key in all_edge_keys:
        edge_values = get_from_all(kedges, edge_key)
        merged_edge = merge_edges(edge_values)
        output["edges"][edge_key] = merged_edge

    return output


def merge_messages(messages):
    """Merge messages."""

    # Build knowledge graph edge IDs so that we can merge duplicates
    for m in messages:
        build_unique_kg_edge_ids(m)

    kgraphs = [m["knowledge_graph"] for m in messages]

    results_deduplicated = connect_knowledge_maps(messages)

    return {
        "query_graph": messages[0]["query_graph"],
        "knowledge_graph": merge_kgraphs(kgraphs),
        "results": results_deduplicated
    }
