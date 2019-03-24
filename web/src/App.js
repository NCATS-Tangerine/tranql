import React, { Component } from 'react';
import { Button } from 'reactstrap';
import { ForceGraph3D } from 'react-force-graph';
import ReactJson from 'react-json-view'
import 'bootstrap/dist/css/bootstrap.min.css';
import 'codemirror/addon/hint/show-hint';
import 'codemirror/addon/hint/sql-hint';
import 'codemirror/addon/hint/show-hint.css'; // without this css hints won't show
import './App.css';
require('create-react-class');
require('codemirror/lib/codemirror.css');
require('codemirror/mode/sql/sql');
var CodeMirror = require('react-codemirror');

class App extends Component {
  /**
   * A TranQL web app.
   */
  constructor(props) {
    /* Create state elements and initialize configuration. */
    super(props);
    this.tranqlURL = "http://localhost:8099/graph/tranql"
    this.codeAutoComplete = this.codeAutoComplete.bind(this);
    this.state = {
      date: new Date(),
      code : "select chemical_substance->gene->disease from \"/graph/gamma/quick\" where disease=\"asthma\"",

      // The graph; populated when a query's executed.
      graph : {
        nodes : [],
        links : []
      },

      // Manage node selection and navigation.
      selectMode: true,
      selectedNode : {},
      selectedLink : {},
      navigateMode: true,
      
      // Set up CodeMirror settings.
      codeMirrorOptions : {        
        lineNumbers: true,
        mode: 'text/x-pgsql', //'text/x-pgsql',
        tabSize: 2,
        readOnly: false,
        extraKeys: {
          'Ctrl-Space': this.codeAutoComplete
        }
      },

      // Configure the 3d force directed graph visualization.
      forceGraph3DOpts : {
        nodeRelSize : 7,
        enableNodeDrag : true
      }
    };
    this.executeQuery = this.executeQuery.bind(this);
    this.setNavMode = this.setNavMode.bind(this);
    this._handleLinkClick = this._handleLinkClick.bind(this);
    this._handleNodeClick = this._handleNodeClick.bind(this);
    this.render = this.render.bind(this);
    this.codemirror = React.createRef ();
  }
  codeAutoComplete (cm) {
    // https://github.com/JedWatson/react-codemirror/issues/52
    var codeMirror = this.codemirror.current.getCodeMirrorInstance ();
    
    // hint options for specific plugin & general show-hint
    // 'tables' is sql-hint specific
    // 'disableKeywords' is also sql-hint specific, and undocumented but referenced in sql-hint plugin
    // Other general hint config, like 'completeSingle' and 'completeOnSingleClick' 
    // should be specified here and will be honored
    const hintOptions = {
      tables: {
        chemical_substance: ['column1', 'column2', 'column3', 'etc', 'select'],
        another_table: ['columnA', 'columnB']
      }, 
      //disableKeywords: true,
      completeSingle: false,
      completeOnSingleClick: false
    };
    
    // codeMirror.hint.sql is defined when importing codemirror/addon/hint/sql-hint
    // (this is mentioned in codemirror addon documentation)
    // Reference the hint function imported here when including other hint addons
    // or supply your own
    //codeMirror.showHint(cm, codeMirror.hint.sql, hintOptions); 
    codeMirror.showHint(cm, codeMirror.hint.sql, hintOptions); 
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
          /* Convert the knowledge graph to a renderable form. */
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
                  origin: node        // keep the orgin node.
                };
              }),
              links : kgraph.knowledge_graph.edges.map(function (edge, index) {
                var weight = Math.round (edge.weight * 100) / 100;
                return {
                  source: edge.source_id,
                  target: edge.target_id,
                  type : edge.type,
                  name : edge.type + " [" + weight + "]",
                  linkOpacity: weight,
                  origin : edge
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
  _handleLinkClick (link) {
    console.log ("-------   select link");
    if (link !== null &&
        this.state.selectedLink !== null &&
//        this.state.selectedLink.source !== link.source_id &&
//        this.state.selectedLink.target !== link.target_id &&
        this.state.selectMode)
    {
      console.log ("-------   select link");
      // Select the node.
      this.setState ((prevState, props) => ({
        selectedNode : { link : link.origin }
      }));
    }
  }
  _handleNodeClick (node) {
    if (this.state.navigateMode) {
      // Navigate camera to selected node.
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
      // Select the node.
      this.setState ((prevState, props) => ({
        selectedNode : { node: node.origin }
      }));
    }
  }
  render() {
    // Render it.
    console.log (this.state);
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
      	  <CodeMirror ref={this.codemirror}
                      value={this.state.code}
                      onChange={this.updateCode}
                      onKeyUp={this.handleKeyUpEvent} 
                      options={this.state.codeMirrorOptions}
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
                          nodeRelSize={this.state.forceGraph3DOpts.nodeRelSize}
                          enableNodeDrag={this.state.forceGraph3DOpts.enableNodeDrag} 
                          onLinkClick={this._handleLinkClick}
                          onNodeClick={this._handleNodeClick} />
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
