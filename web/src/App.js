import React, { Component } from 'react';
import { Button } from 'reactstrap';
//import { ForceGraph, ForceGraphNode, ForceGraphLink } from 'react-vis-force';
import { ForceGraph3D } from 'react-force-graph';
import ReactJson from 'react-json-view'
import './App.css';
import 'bootstrap/dist/css/bootstrap.min.css';

var CodeMirror = require('react-codemirror');
require('codemirror/lib/codemirror.css');
require('codemirror/mode/sql/sql');

var comp = [
  ["here", "hither"],
  ["asynchronous", "nonsynchronous"],
  ["completion", "achievement", "conclusion", "culmination", "expirations"],
  ["hinting", "advive", "broach", "imply"],
  ["function","action"],
  ["provide", "add", "bring", "give"],
  ["synonyms", "equivalents"],
  ["words", "token"],
  ["each", "every"],
]

function synonyms(cm, option) {
  return new Promise(function(accept) {
    setTimeout(function() {
      var cursor = cm.getCursor(), line = cm.getLine(cursor.line)
      var start = cursor.ch, end = cursor.ch
      while (start && /\w/.test(line.charAt(start - 1))) --start
      while (end < line.length && /\w/.test(line.charAt(end))) ++end
      var word = line.slice(start, end).toLowerCase()
      for (var i = 0; i < comp.length; i++) if (comp[i].indexOf(word) !== -1)
        return accept({list: comp[i],
                       from: CodeMirror.Pos(cursor.line, start),
                       to: CodeMirror.Pos(cursor.line, end)})
      return accept(null)
    }, 100)
  })
}

class App extends Component {
  constructor(props) {
    super(props);
    this.tranqlURL = "http://localhost:8099/graph/tranql"
    this.state = {
      date: new Date(),
      code : "select chemical_substance->gene->disease from \"/graph/gamma/quick\" where disease=\"asthma\"",
      graph : {
        nodes : [],
        links : []
      },
      kgraph : {},
      selectMode: true,
      selectedNode : {},
      navigateMode: true
    };
    this.executeQuery = this.executeQuery.bind(this)
    this._handleNodeHover = this._handleNodeHover.bind(this)
    this._handleClick = this._handleClick.bind(this)
    this.render = this.render.bind(this)
    this.setNavMode = this.setNavMode.bind(this)
  }
  setNavMode () {
    this.setState ({
      navigateMode: ! this.state.navigateMode
    });
  }
  executeQuery () {
    console.log (this.state.code);
    fetch(this.tranqlURL, {
      method: "POST",
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify ({
        'query' : this.state.code
      })
    }).then(res => res.json())
      .then(
        (result) => {


          var graph = { nodes : [], links : [] }
          var kgraph = result;
          if (kgraph != null && kgraph.hasOwnProperty ('knowledge_graph')) {
            graph = {
              nodes : kgraph.knowledge_graph.nodes.map(function (node, index) {
                return {
                  id: node.id,
                  type : node.type,
                  radius: 9,
                  name: node.name,
                  origin: node
                };
              }),
              links : kgraph.knowledge_graph.edges.map(function (edge, index) {
                var weight = Math.round (edge.weight * 100) / 100;
                return {
                  source: edge.source_id,
                  target: edge.target_id,
                  type : edge.type,
                  name : edge.type + " [" + weight + "]",
                  linkOpacity: (100 - (weight * 100)) / 100
                };
              })
            }
          };
          this.setState({
            graph: graph
          });
          console.log (result);
        },
        // Note: it's important to handle errors here
        // instead of a catch() block so that we don't swallow
        // exceptions from actual bugs in components.
        (error) => {
          this.setState({
            error
          });
        }
      )
  }
  _handleNodeHover (node) {
  }
  _handleClick (node) {
    console.log ('got click on node ' + node.id)
    if (this.state.navigateMode) {
      // Aim at node from outside it
      const distance = 40;
      const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
      this.fg.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, // new position
        node, // lookAt ({ x, y, z })
        3000  // ms transition duration
      );
    } else if (node !== null && node.id !== undefined && node.id !== null &&
               this.state.selectedNode !== null &&
               this.state.selectedNode.id !== node.id &&
               this.state.selectMode)
    {
      console.log ('node hover');
      this.setState ((prevState, props) => ({
        selectedNode : { node: node.origin }
      }));
    }
  }
  render() {
    // Set up CodeMirror settings.
    var codeMirrorOptions = {
      lineNumbers: true,
      mode: 'sql',
      hintOptions: { hint: synonyms }
    };
    // Set up the 3d vis.
    var forceGraph3DOpts = {
      nodeRelSize : 7,
      enableNodeDrag : true
    }
    // Render it.
    return (
      <div className="App"> 
        <header className="App-header"> 
          <p>TranQL
            <Button id="navModeButton"
                    outline
                    color="primary"
                    onClick={this.setNavMode}>
              { this.state.navigateMode ? "Navigate" : "Select" }
            </Button>
            <Button id="runButton"
                    outline
                    color="success"
                    onClick={this.executeQuery}>
              Run
            </Button>
          </p>
        </header>
        <div>
      	  <CodeMirror ref="editor"
                      value={this.state.code}
                      onChange={this.updateCode}
                      options={codeMirrorOptions}
                      autoFocus={true} />
            <ForceGraph3D id="forceGraph3D"
                          ref={el => { this.fg = el; }}
                          graphData={this.state.graph}
                          height={window.innerHeight * (85 / 100)}
                          nodeAutoColorBy="type"
                          linkAutoColorBy="type"
                          d3AlphaDecay={0.2}
                          strokeWidth={2}
                          linkWidth={2}
                          nodeRelSize={forceGraph3DOpts.nodeRelSize}
                          enableNodeDrag={forceGraph3DOpts.enableNodeDrag} 
                          onNodeHover={this._handleNodeHover}
                          onNodeClick={this._handleClick} />
            <div id="graph"></div>
            <div id="info">
              <ReactJson src={this.state.selectedNode} />
            </div>
        </div>
      </div>
    );
  }
}

export default App;
