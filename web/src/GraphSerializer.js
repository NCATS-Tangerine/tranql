import Chain from './Chain.js';

export default class GraphSerializer {
  static serialize(graph) {
    // Serialize a force graph object to be rerendered retaining its state (does not mutate the graph)
    const cutGraph = JSON.parse(JSON.stringify(graph,(key,value) => {
      if (key !== "allConnections" && key !== "__threeObj" && key !== "__lineObj") return value;
    }));
    return cutGraph;
  }
  static parse(graph) {
    // Parse a serialized force graph object for use
    const newGraph = JSON.parse(JSON.stringify(graph));

    newGraph.links.forEach((link) => {
      // When the force graph processes the links it reassigns these properties to the actual nodes that they refer to
      link.source = link.source.id;
      link.target = link.target.id;
    });
    // Only apply specific render components to it such as constructing the `allConnections` property, which we have to delete
    new Chain([]).handle(newGraph,{});
    return newGraph;
  }
}
