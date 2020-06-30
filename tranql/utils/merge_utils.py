from functools import reduce
import copy

QUESTION_GRAPH_KEY = 'question_graph'
KNOWLEDGE_GRAPH_KEY = 'knowledge_graph'
KNOWLEDGE_MAP_KEY = 'knowledge_map'


def connect_knowledge_maps(responses, query_order):
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
    q_graph_edges = list(reduce(lambda a, b: a + b, map(lambda r: r[QUESTION_GRAPH_KEY]['edges'], responses), []))
    # transform q_graph_edges to
    # source : target : edge
    transformed_q_graph_edges = {}
    for edge in q_graph_edges:
        transformed_q_graph_edges[edge['source_id']] = transformed_q_graph_edges.get(edge['source_id'], {})
        transformed_q_graph_edges[edge['source_id']][edge['target_id']] = transformed_q_graph_edges[edge['source_id']]\
            .get(edge['target_id'], set())
        transformed_q_graph_edges[edge['source_id']][edge['target_id']].add(edge['id'])
    # convert node ids into list, collect score aswell
    score_table = {}
    for bindings in all_knowledge_maps:
        score_key = set()
        nodes = bindings.get('node_bindings', {})
        edges = bindings.get('edge_bindings', {})
        score = bindings.get('score', 0)
        # convert nodes to list
        for concept in nodes:
            curie = nodes[concept]
            curie = curie if isinstance(curie, list) else [curie]
            nodes[concept] = curie
            score_key.add(curie[0])
        for edge_id in edges:
            score_key.add(edges[edge_id][0])
        score_key = frozenset(score_key)
        score_table[score_key] = score


    # Step 2
    # make a transformed graph in a structure that makes it easier to extract the parts for final merged kG graph.
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
        freeze = lambda node_type, node_curie: frozenset({node_type, frozenset(node_curie)})
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
    for path in paths:
        answer = {
            'node_bindings': {},
            'edge_bindings': {}
        }
        for node_data, edge_data in path:
            node_0, node_1 = node_data
            # sometimes for the frozenset data structure the order gets messed up so checking for string
            node_q_id, node_kg_id = [node_0, node_1] if isinstance(node_0, str) else [node_1, node_0]

            answer['node_bindings'][node_q_id] = list(node_kg_id)
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
        for answer in merged_answers:
            node_bindings = list(map(lambda x: answer['node_bindings'][x][0], answer['node_bindings']))
            edge_bindings = list(map(lambda x: answer['edge_bindings'][x][0], answer['edge_bindings']))
            # make sure score key contains all nodes
            filterd = list(filter(lambda x: x not in node_bindings, score_key))
            # make sure edges are also contained
            filterd = list(filter(lambda x: x not in edge_bindings, filterd))
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
