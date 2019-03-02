import json
import logging
import networkx as nx
import os
import sys
from jsonpath_rw import jsonpath, parse
from ndex2 import create_nice_cx_from_networkx
from ndex2.client import Ndex2
from tranql.util import JSONKit

logger = logging.getLogger("ndex")
logger.setLevel(logging.WARNING)

class NDEx:

   """ An interface to the NDEx network catalog. """
   
   def __init__(self, uri="http://public.ndexbio.org"):

      self.jsonkit = JSONKit ()
      
      """ Authenticate to NDEx based on locally stored credentials. """
      ndex_creds = os.path.expanduser("~/.ndex")
      if os.path.exists (ndex_creds):
         with open(ndex_creds, "r") as stream:
            ndex_creds_obj = json.loads (stream.read ())
            logger.debug (f"connecting to ndex as {ndex_creds_obj['username']}")
            account = ndex_creds_obj['username']
            password = ndex_creds_obj['password']
      else:
          raise ValueError ("No ndex credentials found.")
      
      self.uri = uri
      self.session = None
      self.account = account
      self.password = password
      try:
         self.session = Ndex2 (uri, account, password)
         self.session.update_status()
         networks = self.session.status.get("networkCount")
         users = self.session.status.get("userCount")
         groups = self.session.status.get("groupCount")
         logger.debug (f"session: networks: {networks} users: {users} groups: {groups}")
      except Exception as inst:
         logger.error (f"Could not access account {account}")
         raise inst
      
   def publish (self, event):
      return self.publish_graph (name=event.name, graph=event.graph)

   def publish_graph (self, name, graph):
      return self._publish (name=name, graph=graph)
   
   def _publish (self, name, graph):
      
      """ Save a graph to NDEx. First, validate input. """
      assert name, "Missing required network name."
      assert graph, "Graph must be non null. "
      assert len(graph) > 0, "Graph may not be empty."

      """ TODO: Use graph tools to_nx instead. """
      """ Select pieces of interest. """
      """ May require different handling if this needs to run as a workflow step as opposed to a CLI argument. """
      nodes = graph['nodes'] if 'nodes' in graph\
              else self.jsonkit.select (query="$.[*].node_list.[*].[*]",
                                        graph=graph)
      edges = graph['edges'] if 'edges' in graph \
              else self.jsonkit.select (query="$.[*].edge_list.[*].[*]",
                                        graph=graph)

      """ Create the NetworkX graph. """
      g = nx.MultiDiGraph()
      for n in nodes:
         g.add_node(n['id'], attr_dict=n)
      for e in edges:
         g.add_edge (e['source_id'], e['target_id'], attr_dict=e)

      assert len(g.nodes()) > 0, "Cannot save empty graph."
      logger.debug (f" connected: edges: {len(g.edges())} nodes: {len(g.nodes())}")

      """ Convert to CX network. """
      nice_cx = create_nice_cx_from_networkx (g)
      nice_cx.set_name (name)

      """ Upload to NDEx. """
      upload_message = nice_cx.upload_to(self.uri, self.account, self.password)
      logger.debug ("Upload to NDEx complete.")
      logger.debug (f"upload message {upload_message}")
