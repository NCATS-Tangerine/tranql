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
      };


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

class SourceDatabaseFilter extends Actor {
  handle (message, context) {
    // Filter edges by source database:
    var dataSources = context.dataSources;
    var node_ref = [];
    message.graph = {
      links: message.graph.links.reduce (function (result, link) {
        var source_db = link.origin.source_database;
        if (typeof source_db === "string") {
          source_db = [ source_db ];
          link.origin.source_database = source_db;
        }
        var keep_it = true;
        for (var c = 0; c < dataSources.length; c++) {
          if (source_db.includes (dataSources[c].label)) {
            if (! dataSources[c].checked) {
              keep_it = false;
              break;
            }
          }
        }
        if (keep_it) {
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
class LegendFilter extends Actor {
  handle (message, context) {
    console.log(context);
    var links = [];
    var nodes = [];
    /*
      Structure of typeMappings:
        {
          nodes: {
            "{type}":{nodes before LegendFilter}
          },
          links: {
            "{type}":{links before LegendFilter}
          }
      }
    */
    message.typeMappings = {
      nodes:{},
      links:{}
    };
    message.graph.nodes.forEach(node => {
      node.type.forEach(type => {
        if (message.typeMappings.nodes.hasOwnProperty(type)) {
          message.typeMappings.nodes[type].count++;
        }
        else {
          message.typeMappings.nodes[type] = {
            color: null,
            count: 1
          };
        }
      });
    });
    message.graph.links.forEach(link => {
      let type = link.type;
      if (message.typeMappings.links.hasOwnProperty(type)) {
        message.typeMappings.links[type].count++;
      }
      else {
        message.typeMappings.links[type] = {
          color: null,
          count: 1
        };
      }
    });

    let nodeColors = ["#ff0000","#ffff00","#ff00ff","#0000ff","#00ff00"];
    let linkColors = ["#ff0000","#ffff00","#ff00ff","#0000ff","#00ff00"];

    //(zip structure ( [type, {count:x}] ))
    let sortedNodeTypes = Object.entries(message.typeMappings.nodes).sort((a,b) => b[1].count-a[1].count);
    for (let i=0;i<Math.max(nodeColors.length, sortedNodeTypes.length);i++) {
      let nodeType = sortedNodeTypes[i][0];
      let color = nodeColors.shift();
      //set colors of each node
      message.typeMappings.nodes[nodeType].color = color;
      message.graph.nodes.forEach(node => {node.color = color});
    }

    let sortedLinkTypes = Object.entries(message.typeMappings.links).sort((a,b) => b[1].count-a[1].count);
    for (let i=0;i<Math.max(linkColors.length, sortedLinkTypes.length);i++) {
      let linkType = sortedLinkTypes[i][0];
      let color = linkColors.shift();
      //set colors of each link
      message.typeMappings.links[linkType].color = color;
      message.graph.links.forEach(link => {link.color = color});
    }

    console.log(message.typeMappings);


    // Filter nodes that are hidden (NodeFilter source)
    // Couldn't understand the NodeFilter and LinkFilter code so I didn't bother trying to write this feature into the filters with an additional argument or something and reinvoke it
    var nodes = message.graph.nodes.reduce ((acc, node) => {
      //keep node if all of its types are visible
      if (node.type.every(type => context.hiddenTypes.indexOf(type) === -1)) {
        acc.push (node);
      }
      return acc;
    }, []);
    // Remove unused links attached to those nodes
    var node_ids = nodes.map ((n, i) => n.id);
    var links = message.graph.links.reduce ((acc, link) => {
      if (node_ids.includes (link.target) && node_ids.includes (link.source)) {
        acc.push (link);
      }
      return acc;
    }, []);
    var nodes_2 = nodes.reduce ((acc, node) => {
      var count = links.reduce ((lacc, link) => {
        return link.source == node.id || link.target == node.id ? lacc + 1 : lacc;
      }, 0);
      if (count > 0) {
        acc.push (node);
      }
      return acc;
    }, []);

    message.graph = {
      nodes:nodes_2,
      links:links
    };

    var links = [];
    var node_ref = [];
    // Link filter source
    message.graph = {
      links: message.graph.links.reduce (function (result, link) {
        if (context.hiddenTypes.indexOf(link.type) === -1) {
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
    };

    // let nodes = message.graph.nodes.filter(node => node.type.every(type => context.hiddenTypes.indexOf(type) === -1))
    // let links = message.graph.links.filter(link => context.hiddenTypes.indexOf(link.type) === -1),
  }
}
export {
  RenderInit,
  LegendFilter,
  LinkFilter,
  NodeFilter,
  SourceDatabaseFilter,
}
