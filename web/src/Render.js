import Actor from './Actor.js';

class RenderInit extends Actor {
  handle (message, context) {
    message.graph = { nodes: [], links: [] };
    if (message.hasOwnProperty ('knowledge_graph')) {
      message.graph = {
        nodes: message.knowledge_graph.nodes.map(function (node, index) {
          return {
            id: node.id,
            type : node.type,
            radius : 9,
            name: node.name,
            origin: node        // keep the orgin node.
          }; }),
        links: message.knowledge_graph.edges.map(function (edge, index) {
          var weight = Math.round (edge.weight * 100) / 100;
          var opacity = (100 - (100 * weight) ) / 100;
          return {
            source: edge.source_id,
            target: edge.target_id,
            type : edge.type,
            weight : weight,
            name : edge.type + " (w=" + weight + ")",
            linkOpacity: opacity,
            origin : edge
          }; })
      }
    }
  }
} 
class LinkFilter extends Actor {
  handle (message, context) {
    // Filter links:
    var links = [];
    var node_ref = [];
    var min = context.linkWeightRange[0] / 100;
    var max = context.linkWeightRange[1] / 100;
    message.graph = {
      links: message.graph.links.reduce (function (result, link) {
        if (link.weight >= min && link.weight <= max) {
          result.push (link);
          if (! node_ref.includes (link.source)) {
            node_ref.push (link.source);
          }
          if (! node_ref.includes (link.target)) {
            node_ref.push (link.target);
          }
        }
        return result;
      }, []),
      nodes: message.graph.nodes.reduce (function (result, node) {
        if (node_ref.includes (node.id)) {
          result.push (node);
        }
        return result;
      }, [])
    }
  }
}
class NodeFilter extends Actor {
  handle (message, context) {
    // Filter nodes:
    var min = context.nodeDegreeRange[0];
    var max = context.nodeDegreeRange[1];
    var nodes = message.graph.nodes.reduce ((acc, node) => {
      var degree = message.graph.links.reduce ((acc, cur) => {
        return cur.target == node.id ? acc + 1 : acc;
      }, 1);
      if (degree >= min && degree <= max) {
        acc.push (node);
      }
      return acc;
    }, []);
    // Get rid of unused links.
    var node_ids = nodes.map ((n, i) => n.id);
    var links = message.graph.links.reduce ((acc, link) => {
      if (node_ids.includes (link.target) && node_ids.includes (link.source)) {
        acc.push (link);
      }
      return acc;
    }, []);
    // Filter unreferenced nodes.
    var nodes_2 = nodes.reduce ((acc, node) => {
      var count = links.reduce ((lacc, link) => {
        return link.source == node.id || link.target == node.id ? lacc + 1 : lacc;
      }, 0);
      if (count > 0) {
        acc.push (node);
      }
      return acc;
    }, []);


    message.graph = { nodes : nodes_2, links: links };
  }
}

export {
  RenderInit,
  LinkFilter,
  NodeFilter,
}
