import networkx as nx

# Any value offered by TranQLApp that MUST be a promise in the pyodide environment needs to behave the same in a normal environment
class MockPromise:
    def __init__(self, value):
        self._value = value

    def then(self, callback):
        callback(self._value)

# TranQLApp serves as the Python intermediary
# TranQL, the JavaScript intermediary, is injected into Pyodide prior to this script running
# TranQLApp saves the TranQL instance prior to its deletion/withdrawal - still public but no reason to access it
# User communicates with TranQLApp which communicates with the JavaScript intermediary
class TranQLApp:
    def __init__(self):
        try:
            self._TranQLInstance = TranQL
            self._pyodide = True
            self.promise = self._TranQLInstance.promise

        except NameError:
            # For now instead of making a request to the TranQL api just use the interpreter
            from tranql.main import TranQL as TranQLInterpreter
            self._pyodide = False


    def install_module(self, module):
        if self._pyodide:
            return self._TranQLInstance.install_module(module)

    def query(self, query):
        if self._pyodide:
            # This WILL return a Promise<KnowledgeGraph>
            promise = self._TranQLInstance.make_query(query, KnowledgeGraph)
            return promise
        else:
            # This will return a KnowledgeGraph
            return KnowledgeGraph(TranQLInterpreter(options={
                    "dynamic_id_resolution" : True,
                    "asynchronous" : True
                }).execute(query))

    def render(self, knowledge_graph):
        if self._pyodide:
            self._TranQLInstance.set_knowledge_graph(knowledge_graph.get_graph())
        else:
            # TBD
            pass

class KnowledgeGraph:
    def __init__(self, graph):
        # Graph can either be an existing MultiDiGraph or a knowledge graph object
        if isinstance(graph, nx.MultiDiGraph):
            self.net = graph
        else:
            self.build_nx(self._to_dict(graph)) # set and build self.net

    # Manually go in and convert everything that isn't a primitive type (Object, Array) to their python counterparts
    # For some reason, Pyodide does not offer this functionality automatically
    # Also, there doesn't seem to be a way to differentiate between a JavaScript Object or Array in Pyodide or else this could be done recursively
    def _to_dict(self, kg):
        kg = dict(kg)
        for element_type in kg: # nodes, edges
            new_list = []
            for x in kg[element_type]:
                # Note: this does not convert the individual properties of nodes/edges, which remain as primitives/JsProxy's
                new_list.append(dict(x))
            kg[element_type] = new_list
        return kg


    def build_nx(self, kg):
        self.net = nx.MultiDiGraph()
        for node in kg["nodes"]:
            # Store the entire node as its properties so that its data it preserved when converted back to a knowledge graph
            self.add_node(
                node["id"],
                properties=node
            )
        for edge in kg["edges"]:
            # I have no idea why predicates had to be turned into a list a while ago but have to handle that now:
            for predicate in edge["type"]:
                self.add_edge(
                    edge["source_id"],
                    predicate,
                    edge["target_id"],
                    properties=edge
                )

    def build_kg(self):
        kg = {
            "nodes": [],
            "edges": []
        }
        for node in self.net.nodes(data=True):
            kg["nodes"].append(
                node[1]["attr_dict"]
            )
        for edge in self.net.edges(data=True):
            kg["edges"].append(
                edge[2]
            )
        return kg

    def add_edge (self, start, predicate, end, properties={}):
        return self.net.add_edge (start, end, key=predicate, **properties)
    def add_node (self, identifier, label=None, properties={}):
        node = self.net.add_node (identifier, attr_dict=properties)
        return node
    def has_node (self, identifier):
        return identifier in self.net.nodes
    def get_node (self, identifier, properties=None):
        nodes = self.net.nodes(data=True)
        filtered = [i for i in nodes if i[0] == identifier]
        return filtered[0] if len(filtered) > 0 else None
    def get_edge (self, start, end, properties=None):
        result = None
        for e in self.net.edges:
            #print (f"-----    {start} {end} | {e[0]} {e[2]}")
            if e[0] == start and e[1] == end:
                result = e
                break
        return result
    def get_nodes (self,**kwargs):
        return self.net.nodes(**kwargs)
    def get_edges (self,**kwargs):
        return self.net.edges(keys=True,**kwargs)
    def delete (self):
        self.net.clear ()


    # Graph operations (see https://networkx.github.io/documentation/stable/reference/algorithms/operators.html)
    def simple_union(self, other_kg):
        # Returns a KnowledgeGraph of the simple union of self and other_kg (node sets do not have to be disjoint)
        return KnowledgeGraph(nx.compose(self.net, other_kg.net))

    def union(self, other_kg):
        # Returns a KnowledgeGraph of the union of self and other_kg  (node sets must be disjoint)
        return KnowledgeGraph(nx.union(self.net, other_kg.net))

    def disjoint_union(self, other_kg):
        # Returns a KnowledgeGraph of the disjoint union of self and other_kg
        return KnowledgeGraph(nx.disjoint_union(self.net, other_kg.net))

    def intersection(self, other_kg):
        # Returns a KnowledgeGraph containing only edges that exist in both self and other_kg
        return KnowledgeGraph(nx.intersection(self.net, other_kg.net))

    def difference(self, other_kg):
        # Returns a KnowledgeGraph containing edges that exist in self but not in other_kg
        return KnowledgeGraph(nx.difference(self.net, other_kg.net))

    def symmetric_difference(self, other_kg):
        # Returns a KnowledgeGraph containing edges that exist in self or other_kg but not both
        return KnowledgeGraph(nx.symmetric_difference(self.net, other_kg.net))

    def __add__(self, other):
        return self.simple_union(other)

    def __sub__(self, other):
        return self.difference(other)

tranql = TranQLApp()
