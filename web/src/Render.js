import Actor from './Actor.js';
import { groupBy, changeHue } from './Util.js';
import uuid from 'uuid/v4';

class RenderInit extends Actor {
  handle (message, context) {
    message.graph = { nodes: [], links: [] };
    if (message.hasOwnProperty ('knowledge_graph')) {
      message.graph = {
        nodes: message.knowledge_graph.nodes.map(function (node, index) {
          return {
            id: node.id,
            type : Array.isArray(node.type) ? node.type : [node.type],
            radius : 9,
            name: node.name,
            origin: node        // keep the origin node.
          }; }),
        links: message.knowledge_graph.edges.map(function (edge, index) {
          var weight = edge.weight === undefined ? null : Math.round (edge.weight * 100) / 100;
          var opacity = (100 - (100 * weight) ) / 100;
          return {
            source: edge.source_id,
            target: edge.target_id,
            type : Array.isArray(edge.type) ? edge.type : [edge.type],
            weight : weight,
            name : edge.type + " (w=" + weight + ")",
            linkOpacity: opacity,
            origin : edge
          }; })
      };


    }
  }
}

class RenderSchemaInit extends Actor {
  handle(message, context) {
    message.knowledge_graph = {
      nodes: message.knowledge_graph.nodes.map((node) => {
        if (typeof node === "string") {
          return {
            id: node,
            type: node,
            name: node
          };
        }
        else {
          return node;
        }
      }),
      edges: message.knowledge_graph.edges.reduce((acc, edge) => {
        // TODO fix? Can't draw edges from a node to itself
        if (Array.isArray(edge)) {
          if (edge[0] !== edge[1]) {
            acc.push({
              source_id: edge[0],
              target_id: edge[1],
              type: edge[2],
              weight: 1
            });
          }
        }
        else {
          acc.push(edge);
        }
        return acc;
      }, [])
   };
  }
}

class IdFilter extends Actor {
  /**
   * Links do not possess unique identifiers and although the force graph seems to generate uuids for them I'm unsure if this they are persistent/safe to use.
   * Some things may require that both nodes and links can be distinguished from one another, so this filter goes through and generates uuids for each link.
   *
   */
  handle (message, context) {
    const id = {
      _ids: [],
      get() {
        const id = uuid();
        if (this._ids.includes(id)) {
          return this.get();
        }
        else {
          this._ids.push(id);
          return id;
        }
      }
    };
    message.graph.links.forEach((link) => {
      link.id = id.get();
    });
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
        if (link.weight === null || link.weight >= min && link.weight <= max) {
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
  }
}
class NodeFilter extends Actor {
  handle (message, context) {
    // Filter nodes:
    var min = context.nodeDegreeRange[0];
    var max = context.nodeDegreeRange[1];
    var nodes = message.graph.nodes.reduce ((acc, node) => {
      var degree = message.graph.links.reduce ((acc, cur) => {
        return cur.target === node.id ? acc + 1 : acc;
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
        return link.source === node.id || link.target === node.id ? lacc + 1 : lacc;
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
        if (typeof source_db === "undefined") {
          keep_it = true
        }
        else {
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
    var links = [];
    var nodes = [];
    /*
      Structure of typeMappings:
        {
          nodes: {
            `type`:{color,quantity}
          },
          links: {
            `type`:{color,quantity}
          }
      }
    */
    let typeMappings = {
      nodes:{},
      links:{}
    };
    for (let elementType in message.graph) {
      let elements = message.graph[elementType];
      elements.forEach(element => {
        if (typeof element.type === "string")  element.type = [element.type];
        element.type.forEach(type => {
          if (typeMappings[elementType].hasOwnProperty(type)) {
            typeMappings[elementType][type].quantity++;
          }
          else {
            typeMappings[elementType][type] = {
              color: null,
              quantity: 1
            };
          }
        });
      });
    }

    let colors = [
      "#7ac984","#ffef89","#8ecccc","#f7a8d8","#9bafff","#fabebe","#ffe47c","#aaffc3","#f79b9b","#ffd24c",
      "#848ec9","#ff8eb4","#d195db","#cddc39","#c69393","#e6beff", "#cd546b", "#996ec3", "#7aa444", "#4cab98",
      "#c27f3c", "#8cc8b1", "#aabbea", "#7bcaed", "#7bc950", "#df99f0"
    ];


    // The following code iterates over first the nodes and then the links assigning every type a color.
    // It does this by manipulating the hues of the `colors` array every time it iterates over them.
    // Links are identical to node colors except in hue which they have `hueShift` more.
    // Every n iteration of the colors array, it shifts the colors down by -n*hueShift hue.
    // Everytime it shifts past 360 hue (the maximum hue in HSL) from the initial color is known as a cycle.
    // Every k cycle it shifts by k * (hueShift/(k+1)) more.

    const hueShift = 50;
    let overallColors = [];
    let index = 0;
    // (Zip structure ( [type, {quantity:x}] ))
    for (let elementType in typeMappings) {
      let sortedTypes = Object.entries(typeMappings[elementType]).sort((a,b) => b[1].quantity-a[1].quantity);
      sortedTypes.forEach((obj) => {
        // let index = elementType === "nodes" ? i : colors.length-(i+1);
        let type = obj[0];

        let color;

        if (index >= colors.length) {
          // If run out of colors, start recycling but shift the hues down. Make sure to shift the hues. Ensure that after multiple times iterating colors you continue to shift more.
          // Note - this method runs out of colors and starts cycling after hue has been shifted over 360
          let cycles = Math.ceil(index/colors.length);

          let totalShift = cycles*hueShift;
          let totalHueCycles = Math.floor(totalShift/360);

          let hueCycleShift = totalHueCycles * (hueShift / (totalHueCycles + 1));

          // console.log(totalHueCycles*hueCycleShift, totalShift, cycles);

          let ind = index % colors.length; // Restart the index for color array
          color = changeHue(colors[ind], -totalShift-(hueCycleShift));
        }
        else {
          color = colors[index];
        }
        if (elementType === "links") {
          // color = changeHue(color, hueShift*2); //reuse the same color but shift its hue by enough that it's distinguishable as a completely different color
        }
        // Set colors of each type
        typeMappings[elementType][type].color = color;
        overallColors.push(color);
        index++;
      });
    }
    // console.log(overallColors.length,new Set(overallColors).size);
    message.graph.nodes.forEach(node => {node.color = typeMappings.nodes[node.type[0]].color});
    message.graph.links.forEach(link => {link.color = typeMappings.links[link.type].color});

    if (!message.hasOwnProperty('hiddenTypes')) {
      // If this is the first time the message is processed by the render chain, give it the hiddenTypes property.
      message.hiddenTypes = {
        "nodes":[],
        "links":[]
      };
    }

    // Filter nodes that are hidden (NodeFilter source)
    // Couldn't understand the NodeFilter and LinkFilter code so I didn't bother trying to write this feature into the filters with an additional argument or something and reinvoke it
    var nodes = message.graph.nodes.reduce ((acc, node) => {
      //keep node if all of its types are visible
      if (node.type.every(type => message.hiddenTypes.nodes.indexOf(type) === -1)) {
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
        return link.source === node.id || link.target === node.id ? lacc + 1 : lacc;
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
        link.type = typeof link.type === "string" ? [link.type] : link.type;
        link.type.forEach(type => {
          if (message.hiddenTypes.links.indexOf(type) === -1) {
            result.push (link);
            if (! node_ref.includes (link.source)) {
              node_ref.push (link.source);
            }
            if (! node_ref.includes (link.target)) {
              node_ref.push (link.target);
            }
          }
        });
        return result;
      }, []),
      nodes: message.graph.nodes.reduce (function (result, node) {
        if (node_ref.includes (node.id)) {
          result.push (node);
        }
        return result;
      }, []),
    };
    for (let elementType in message.graph) {
      let elements = message.graph[elementType];
      elements.forEach(element => {
        if (typeof element.type === "string")  element.type = [element.type];
        element.type.forEach(type => {
          if (typeMappings[elementType][type].hasOwnProperty('actualQuantity')) {
            typeMappings[elementType][type].actualQuantity++;
          }
          else {
            typeMappings[elementType][type].actualQuantity = 1;
          }
        });
      });
    }
    message.graph.typeMappings = typeMappings;
    message.graph.hiddenTypes = message.hiddenTypes;
  }
}
class CurvatureAdjuster extends Actor {
  handle (message, context) {
    // Goes through and finds node pairs that have multiple links between them and gives them a curvature property so that each link is visible.
    // Additionally, gives curvature to self-referencing Links
    // if (!context.curvedLinks) {
    //   // Don't run when feature is turned off
    //   return;
    // }
    let groups = groupBy(message.graph.links,i=>[i.source,i.target].sort());
    groups.forEach(group => {
      // Join all the link names together
      let allTypesString = group.map(link => link.name).join(",<br/>");
      group.forEach((link, index) => {
        // Group length of 1 would result in curvature of 1, which generates a semicircle.
        // link.curvature = group.length === 1 ? 0 : (i+1) / group.length;
        link.concatName = allTypesString;
        link.allConnections = group;
        if (context.curvedLinks) {
          link.curvature = index/group.length;
          link.rotation = (Math.PI*2)/(index/group.length);
        }
      });
    });
  }
}

export {
  RenderInit,
  RenderSchemaInit,
  IdFilter,
  LegendFilter,
  LinkFilter,
  NodeFilter,
  SourceDatabaseFilter,
  CurvatureAdjuster
}
