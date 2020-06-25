# import networkx as nx

# Any value offered by TranQLApp that MUST be a promise in the pyodide environment needs to behave the same in a normal environment
class MockPromise:
    def __init__(self, value):
        self._value = value

    def then(self, callback):
        callback(self._value)

class TranQLApp:
    def __init__(self):
        try:
            self._TranQLInstance = TranQL
            self._pyodide = True
        except NameError:
            from tranql.main import TranQL as TranQLInterpreter
            self._pyodide = False

    def query(self, query):
        if self._pyodide:
            # This WILL return a Promise<KnowledgeGraph>
            promise = self._TranQLInstance.make_query(query, KnowledgeGraph)
            return promise
        else:
            # This will return a MockPromise<KnowledgeGraph>
            return MockPromise(
                KnowledgeGraph(TranQLInterpreter(options={
                    "dynamic_id_resolution" : True,
                    "asynchronous" : True
                }).execute(query))
            )

    def render(self, knowledge_graph):
        if self._pyodide:
            self._TranQLInstance.set_knowledge_graph(knowledge_graph.get_graph())
        else:
            # TBD
            pass

class KnowledgeGraph:
    def __init__(self, kg):
        # Make sure it is a native dict if provided by Pyodide
        self.net = self.build_nx(dict(kg))

        # Place holder until networkx
        self._kg = kg

    def build_nx(self, kg):
        return None

    def get_graph(self):
        return self._kg

    def union(self, other_kg):
        return self.net.union(other_kg)

    def difference(self, other_kg):
        return self.net.difference(other_kg)

    def symmetric_difference(self, other_kg):
        return self.net.symmetric_difference(other_kg)

# class NetworkxGraph:
#     def __init__(self):
#         self.net = nx.MultiDiGraph ()
#     def add_edge (self, start, predicate, end, properties={}):
#         return self.net.add_edge (start, end, key=predicate, **properties)
#     def add_node (self, identifier, label=None, properties={}):
#         node = self.net.add_node (identifier, attr_dict=properties)
#         return node
#     def has_node (self, identifier):
#         return identifier in self.net.nodes
#     def get_node (self, identifier, properties=None):
#         nodes = self.net.nodes(data=True)
#         filtered = [i for i in nodes if i[0] == identifier]
#         return filtered[0] if len(filtered) > 0 else None
#     def get_edge (self, start, end, properties=None):
#         result = None
#         for e in self.net.edges:
#             #print (f"-----    {start} {end} | {e[0]} {e[2]}")
#             if e[0] == start and e[1] == end:
#                 result = e
#                 break
#         return result
#     def get_nodes (self,**kwargs):
#         return self.net.nodes(**kwargs)
#     def get_edges (self,**kwargs):
#         return self.net.edges(keys=True,**kwargs)
#     def delete (self):
#         self.net.clear ()
#     def commit (self):
#         pass

tranql = TranQLApp()
