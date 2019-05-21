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
          message.typeMappings.nodes[type].quantity++;
        }
        else {
          message.typeMappings.nodes[type] = {
            color: null,
            quantity: 1
          };
        }
      });
    });
    message.graph.links.forEach(link => {
      let type = link.type;
      if (message.typeMappings.links.hasOwnProperty(type)) {
        message.typeMappings.links[type].quantity++;
      }
      else {
        message.typeMappings.links[type] = {
          color: null,
          quantity: 1
        };
      }
    });

    let nodeColors = ["#5B35C3","#23F1DD","#9A1004","#B73C53","#FA7196","#B9F88F","#25D459","#6754A9","#589E03","#518C06","#1518A3","#808399","#CAE220","#559805","#0BBE00","#E2B1B0","#990A8A","#726615","#08811F","#AA6B05","#713AFE","#A1F086","#2084C4","#327429","#9315E8","#C5BC8A","#DE5CEC","#4EBC70","#558F40","#F490CC","#26E45B","#B1735A","#010B4C","#DF75DB","#BBEE4E","#A9BD14","#B6CB11","#DF6E76","#DD837B","#D3A054","#FAD663","#BFD6B5","#EBCA8E","#220D2C","#FE6EC9","#86FC0F","#4A5BD9","#E31BBC","#209FDA","#AA968A","#6B142E","#C195CC","#85D2F4","#F98ACA","#B4C95E","#E153F0","#22C9AA","#A53D4D","#68F295","#B8E14A","#B469B7","#9FE21D","#F66524","#2F47B1","#46422E","#5A8352","#E0DF43","#92D8D0","#089CE6","#533AFB","#BC691D","#1553D5","#6FCE1A","#2084D5","#B25563","#C4918B","#011EC9","#1EB570","#F1EB87","#9A7379","#267E45","#D11231","#F44191","#929FC9","#F029EB","#31F876","#73CB5E","#3E0063","#870DD0","#3EFD91","#F8E79A","#6098E2","#33060F","#3676C9","#C20926","#B19089","#9798DB","#0E8D40","#63FD25","#1C8BB4","#3125B7","#30B9E4","#B4B884","#43C6A5","#30AA77","#633A26","#079C3D","#81601A","#E8B10D","#E3B9BD","#61D162","#D67E28","#A0C7D8","#3A52F1","#D844C2","#0EFB56","#87022B","#FC9965","#1FFA7B","#B39A8D","#2293E5","#02018B","#DF6DCE","#ABE90A","#E658C7","#6B859A","#7974F3","#9F6E2F","#A6CD57","#2BBA23","#07CA65","#89BFD7","#29D820","#72B13E","#5B993B","#D740EB","#F9C513","#96FF3B","#E43B07","#F32BDD","#1AD0B9","#0B196E","#15F8CA","#8895B6","#ABD22E","#972CDC","#BBAF0F","#F6CD2F","#B5048B","#406405","#405D43","#47DA64","#DF0F02","#C9497F","#EDE44E","#D8209B","#14CA9D","#45331C","#48754C","#B5B2E1","#D9D9D4","#B432A8","#BECB3D","#653BB8","#31A7CB","#74538F","#571A8E","#E788F2","#707845","#8F2304","#8DF194","#106A8C","#0CB778","#53A45C","#B26927","#689BE5","#585EB8","#8168B1","#237AB5","#C03234","#B94046","#E22956","#654FCF","#383F2A","#ADC20D","#49B0DF","#11160E","#7F5685","#EA58DC","#54F8D3","#D34D1F","#5EE460","#7B633F","#8E8311","#590A90","#CE31A9","#6415DC","#D334F9","#803881","#73AD0F","#F5E074","#917DFF","#CB99BB","#E471DD","#C40503","#1DF356","#5F10EA","#B7E91D","#DDDB8F","#1247D1","#E74DFB","#05B357","#79EF99","#62F6F9","#BE774F","#BBFC91","#7950E7","#0F5329","#5BF667","#93970E","#1BF3CC","#4CB0B3","#387474","#399F6F","#DBF3F2","#BBBA5F","#0D2ABD","#66E314","#0BFE35","#9A070D","#47D52C","#DCD681","#22EDD1","#FC76C2","#436FC9","#696F0D","#032B80","#465F19","#F43EF2","#AE30B0","#69FBC8","#4081EA","#76344F","#60B301","#C33438","#E463A2","#D06F1D","#2FCF52","#DEADFD","#E3787A","#9DAA0A","#0C3F40","#B1A80A","#D11CE8","#E43979","#40DA2E","#21567B","#B37E6D","#0C5E62","#41BD22","#F4EB22","#CFC683","#5E127B","#9E18CD","#66132F","#02070E","#195623","#CFBC32","#731C28","#13F0ED","#058EE8","#E21F33","#2DF6E9","#BE077F","#2BD9B6","#002EA7","#63B188","#E1A794","#85B6BD","#A67AF8","#B7715F","#DA4B01","#224D98","#C7685F","#8D4779","#9A6661","#CAA9E2","#055D56","#31AACE","#04EF62","#983C0A","#042713","#157BE6","#882F77","#157A22","#F41604","#49B44F","#96BC18","#3E8A17","#3ED62C","#A02A88","#0D8E59","#22C884","#6297C9","#496A98","#B7BBB9","#9BC048","#1EDA0E","#26DBD9","#FC3693","#D4DBB4","#723CED","#20A73A","#26E7A7","#A12830","#1AE1BC","#8DCF70","#7C81C7","#DDDEBF","#4BE4E7","#7874A2","#482CCE","#EB89B8","#039B5E","#7337E2","#6B6BC2","#A2DD7A","#1E7E0A","#4E9056","#D580B7","#DD8D6A","#64EBB6","#23FAA5","#33CC2E","#A31326","#723B0A","#691BFA","#F66ED9","#AA61D2","#0FA61F","#B94D53","#81C0F8","#3CE576","#3953A4","#49BE37","#A22259","#BECE64","#699529","#1189F8","#ED4CA2","#411FC2","#528AE6","#8968D1","#6EAF84","#F578CF","#3B6F44","#715901","#19977A","#80DC02","#4EDCF2","#DC603A","#1A0744","#A2AFBD","#F5D204","#22CC48","#04C422","#29032D","#94220C","#F35671","#8DE424","#6FAD94","#95D554","#3F0BAF","#354A6C","#7B6789","#5E0464","#213E01","#74FEC8","#84A3A4","#D01F9E","#16E312","#0C7DFC","#0FC6FD","#595B30","#8A9003","#00D5C3","#48C9E9","#2C9B87","#B71BB9","#303502","#D35476","#2753AF","#9438FE","#73587F","#083D4D","#C0528F","#0F4F16","#F04E75","#613D90","#D962D4","#D911C6","#EB56E8","#113670","#C3EB54","#A31CF1","#E85E4E","#E7DD06","#E1A5D9","#ED941E","#993444","#641588","#3D8A2C","#384EA7","#E6BDF4","#9DD276","#531E73","#3908E6","#24C5A0","#D8B549","#EE0E72","#B46AD2","#390A81","#597941","#40B3DA","#1D2FB1","#BDFFAB","#52F436","#E85FF1","#20EAC1","#B44B74","#565FDB","#83CBF8","#10FB37","#91283F","#90DD79","#7CBB45","#ED09F3","#4C5D2D","#9FA866","#B1866F","#EC333F","#C70179","#276C27","#35D27F","#ABD52F","#A8E414","#F9D358","#4D89C5","#504159","#F35840","#205812","#D129A6","#AAA995","#978EE1","#75D3D4","#DDD264","#577A04","#5A4D11","#86032D","#3C1C31","#193108","#99383D","#E56AEF","#D9B88E","#76F622","#74A059","#3DBEF6","#3E9FA6","#73D42C","#9796BB","#8D3A02","#638CCB","#CBCC4E","#E88374","#16A9DC","#9C2DAA","#772DAD","#008728","#5AB724","#143278","#427157","#8CB38D","#7ABC4C","#951464","#95B1F9","#B45CA7","#DEC9F2","#5AB541","#288AD4","#CBC84D","#552BE6","#EBEB6F","#E0C1F8","#FCEBB0","#B17920","#998BC3","#0AB4D9","#BFDDE7","#5BD0CE","#AC0F21"]

    let linkColors = nodeColors.slice()

    //(zip structure ( [type, {quantity:x}] ))
    let sortedNodeTypes = Object.entries(message.typeMappings.nodes).sort((a,b) => b[1].quantity-a[1].quantity);
    for (let i=0;i<Math.min(nodeColors.length, sortedNodeTypes.length);i++) {
      let nodeType = sortedNodeTypes[i][0];
      let color = nodeColors.shift();
      //set colors of each node
      message.typeMappings.nodes[nodeType].color = color;
    }

    let sortedLinkTypes = Object.entries(message.typeMappings.links).sort((a,b) => b[1].quantity-a[1].quantity);
    for (let i=0;i<Math.min(linkColors.length, sortedLinkTypes.length);i++) {
      let linkType = sortedLinkTypes[i][0];
      let color = linkColors.shift();
      //set colors of each link
      message.typeMappings.links[linkType].color = color;
    }
    message.graph.nodes.forEach(node => {node.color = message.typeMappings.nodes[node.type[0]].color});
    message.graph.links.forEach(link => {link.color = message.typeMappings.links[link.type].color});


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
  }
}
export {
  RenderInit,
  LegendFilter,
  LinkFilter,
  NodeFilter,
  SourceDatabaseFilter,
}
