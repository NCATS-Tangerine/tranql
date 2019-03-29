import React, { Component } from 'react';
import { Button } from 'reactstrap';
import { Modal } from 'react-bootstrap';
import { ForceGraph3D, ForceGraph2D } from 'react-force-graph';
import ReactJson from 'react-json-view'
import logo from './static/images/tranql.png'; // Tell Webpack this JS file uses this image
import { IoIosSettings, IoIosPlayCircle, IoIosNavigate } from 'react-icons/io';
import ReactTable from "react-table";
import Tooltip from 'rc-tooltip';
import Slider, { Range } from 'rc-slider';
import SplitPane from 'react-split-pane';
import Cache from './Cache.js';
import 'rc-slider/assets/index.css';
import "react-table/react-table.css";
import 'bootstrap/dist/css/bootstrap.min.css';
import 'codemirror/addon/hint/show-hint';
import 'codemirror/addon/hint/sql-hint';
import 'codemirror/addon/hint/show-hint.css'; // without this css hints won't show
import './App.css';
require('create-react-class');
require('codemirror/lib/codemirror.css');
require('codemirror/mode/sql/sql');
var CodeMirror = require('react-codemirror');

const sliderStyles = {
  root: {
    display: 'flex',
    height: 300,
  },
  slider: {
    padding: '0px 22px',
  },
};
 
const createSliderWithTooltip = Slider.createSliderWithTooltip;
const Handle = Slider.Handle;
const handle = (props) => {
  const { value, dragging, index, ...restProps } = props;
  return (
    <Tooltip
      prefixCls="rc-slider-tooltip"
      overlay={value}
      visible={dragging}
      placement="top"
      key={index}
    >
      <Handle value={value} {...restProps} />
    </Tooltip>
  );
};
function openInNewTab(url) {
  var win = window.open(url, '_blank');
  win.focus();
}

class App extends Component {
  /**
   * A TranQL web app.
   */
  constructor(props) {
    /* Create state elements and initialize configuration. */
    super(props);
    this.tranqlURL = "http://localhost:8100";
    this.robokop_url = "http://robokop.renci.org";
    
    // Query editor support.
    this._getModelConcepts = this._getModelConcepts.bind (this);
    this._getModelRelations = this._getModelRelations.bind (this);
    this._codeAutoComplete = this._codeAutoComplete.bind(this);
    this._updateCode = this._updateCode.bind (this);
    this._executeQuery = this._executeQuery.bind(this);
    this._translateGraph = this._translateGraph.bind (this);

    // The visualization
    this._setNavMode = this._setNavMode.bind(this);
    this._renderForceGraph = this._renderForceGraph.bind (this);
    this._renderForceGraph2D = this._renderForceGraph2D.bind (this);
    this._renderForceGraph3D = this._renderForceGraph3D.bind (this);
    this._handleNodeClick = this._handleNodeClick.bind(this);
    this._handleLinkClick = this._handleLinkClick.bind(this);

    // Settings management
    this._handleShowModal = this._handleShowModal.bind (this);
    this._handleCloseModal = this._handleCloseModal.bind (this);    
    this._handleUpdateSettings = this._handleUpdateSettings.bind (this);
    this._hydrateState = this._hydrateState.bind (this);
    this._onMinLinkWeightChange = this._onMinLinkWeightChange.bind (this);
    this._onMinLinkWeightAfterChange = this._onMinLinkWeightAfterChange.bind (this);
    this._analyzeAnswer = this._analyzeAnswer.bind (this);
    this._renderTable = this._renderTable.bind (this);    
    this._cacheRead = this._cacheRead.bind (this);

    // Component rendering.
    this.render = this.render.bind(this);

    // Create code mirror reference.
    this._codemirror = React.createRef ();

    // Cache graphs locally using IndexedDB web component.
    this._cache = new Cache ();
    
    // Configure initial state.
    this.state = {
      code : "select chemical_substance->gene->disease\n  from \"/graph/gamma/quick\"\n where disease=\"asthma\"",

      // Concept model concepts and relations.
      modelConcepts : [],
      modelRelations : [],
      
      // The graph; populated when a query's executed.
      graph : {
        nodes : [],
        links : []
      },
      minLinkWeight : 0,
      
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
          'Ctrl-Space': this._codeAutoComplete
        }
      },

      // Configure the 3d force directed graph visualization.
      visMode : '3D',
      useCache : true,
      forceGraphOpts : {
        nodeRelSize : 7,
        enableNodeDrag : true
      },

      // Settings modal
      //modalIsOpen: false
      showModal : false
    };

    // Populate concepts and relations metadata.
    this._getModelConcepts ();
    this._getModelRelations ();
  }
  _onMinLinkWeightChange (value) {
    this.setState({ minLinkWeight : value});
    localStorage.setItem ("minLinkWeight", JSON.stringify (value));
  }
  _onMinLinkWeightAfterChange (value) {
    console.log("--after update", value);
    //this.props.update(this.state); //    this.setState({ minLinkWeight : value});
  }
  _hydrateState () {
    // for all items in state
    for (let key in this.state) {
      // if the key exists in localStorage
      if (localStorage.hasOwnProperty(key)) {
        // get the key's value from localStorage
        let value = localStorage.getItem(key);

        // parse the localStorage string and setState
        try {
          value = JSON.parse(value);
          this.setState({ [key]: value });
        } catch (e) {
          // handle empty string.
          console.log (" setting " + key + " => " + value);
          this.setState({ [key]: value });
        }
      }
    }
  }
  _cacheRead (key) {
    var result = null;
    if (localStorage.hasOwnProperty(key)) {
      // get the key's value from localStorage
      let value = localStorage.getItem(key);
      try {
        result = JSON.parse(value);
      } catch (e) {
        // handle empty string.
        result = value;
      }
    }
    return result;
  }
  /**
   * Callback for the query editor to set the value of the code.
   */
  _updateCode (newCode) {
    this.setState({
      code: newCode
    });
  }
  /**
   * Callback for handling autocompletion within the query editor.
   */
  _codeAutoComplete (cm) {
    // https://github.com/JedWatson/react-codemirror/issues/52
    var codeMirror = this._codemirror.current.getCodeMirrorInstance ();
    
    // hint options for specific plugin & general show-hint
    // 'tables' is sql-hint specific
    // 'disableKeywords' is also sql-hint specific, and undocumented but referenced in sql-hint plugin
    // Other general hint config, like 'completeSingle' and 'completeOnSingleClick' 
    // should be specified here and will be honored
    var tables = {};
    for (var c = 0; c < this.state.modelConcepts.length; c++) {
      var concept = this.state.modelConcepts[c];
      tables[concept] = [ /** column names, whatever those are in this context, go here. **/ ];
    }
    const hintOptions = {
      tables: tables,
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
  /**
   * Set the navigation / selection mode.
   */
  _setNavMode () {
    this.setState ({
      navigateMode: ! this.state.navigateMode
    });
  }
  /**
   * In depth analysis of an answer.
   */
  _analyzeAnswer (message) {
    // We didn't find it in the cache. Run the query.
    fetch(this.robokop_url + '/api/simple/view/', {
      method: "POST",
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify (message)
    }).then(res => res.text())
      .then(
        (result) => {
          /* Convert the knowledge graph to a renderable form. */
          console.log (result);
          openInNewTab (result);
        },
        // Note: it's important to handle errors here
        // instead of a catch() block so that we don't swallow
        // exceptions from actual bugs in components.
        (error) => {
          this.setState({
            error
          });
        }
      );
  }
  /**
   * Execute a TranQL query.
   */
  _executeQuery () {
    console.log ("--query: ", this.state.code);
    // First check if it's in the cache.
    var cachePromise = this._cache.read (this.state.code);
    cachePromise.then (
      function success (result) {
        console.log ("---- cache hit.", result);
        if (result.length > 0) {
          // Translate the knowledge graph given current settings.
          this._translateGraph (result[0].data)
        } else {
          // We didn't find it in the cache. Run the query.
          fetch(this.tranqlURL + '/tranql/query', {
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
                this._translateGraph (result);
                this._cache.write (this.state.code, result);
                this._analyzeAnswer (result);
                console.log ("new tab: " + result);
              },
              // Note: it's important to handle errors here
              // instead of a catch() block so that we don't swallow
              // exceptions from actual bugs in components.
              (error) => {
                this.setState({
                  error
                });
              }
            );
        }
      }.bind(this),
      function error (result) {
        console.log ("-- error", result);
      });
  }
  _translateGraph (kgraph) {    
    var graph = { nodes : [], links : [] }
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
            weight : weight,
            name : edge.type + " [" + weight + "]",
            linkOpacity: weight, //(100 - ( weight * 100 )) / 100, //weight
            origin : edge
          };
        })
      }


      // Make a chain of responsibility:
      // Filter links:
      var links = [];
      var node_ref = [];
      var threshold = this.state.minLinkWeight / 100;
      for (var c = 0; c < graph.links.length; c++) {
        var link = graph.links[c];
        if (link.weight >= threshold) {
          links.push (link);
          if (! node_ref.includes (link.source)) {
            node_ref.push (link.source);
          }
          if (! node_ref.includes (link.target)) {
            node_ref.push (link.target);
          }
        }
      }
      graph.links = links;
      var nodes = [];
      for (var c = 0; c < graph.nodes.length; c++) {
        if (node_ref.includes (graph.nodes[c].id)) {
          nodes.push (graph.nodes[c]);
        }
      }
      graph.nodes = nodes;      
    }
    this.setState({
      graph: graph
    });
  }
  /**
   * Get the concept model.
   */
  _getModelConcepts () {
    fetch(this.tranqlURL + '/tranql/model/concepts', {
      method: "POST",
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify ({
        'query' : ''
      })
    }).then(res => res.json())
      .then(
        (result) => {
          this.setState({
            modelConcepts: result
          });
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
  /**
   * Get the concept model relations.
   */
  _getModelRelations () {
    fetch(this.tranqlURL + '/tranql/model/relations', {
      method: "POST",
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify ({
        'query' : ''
      })
    }).then(res => res.json())
      .then(
        (result) => {
          this.setState({
            modelRelations: result
          });
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
    if (link !== null &&
        this.state.selectedLink !== null &&
//        this.state.selectedLink.source !== link.source_id &&
//        this.state.selectedLink.target !== link.target_id &&
        this.state.selectMode)
    {
      // Select the node.
      this.setState ((prevState, props) => ({
        selectedNode : { link : link.origin }
      }));
      document.getElementById ('info').style.display = 'block';
    }
  }
  _handleNodeClick (node) {
    if (this.state.navigateMode && this.state.visMode === '3D') {
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
      document.getElementById ('info').style.display = 'block';
    }
  }
  _renderForceGraph () {
    return this.state.visMode === '3D' ?
      this._renderForceGraph3D () :
      this._renderForceGraph2D ()
  }
  _renderForceGraph3D () {
      return <ForceGraph3D id="forceGraph3D"
                           ref={el => { this.fg = el; }}
                           graphData={this.state.graph}
                           width={window.innerWidth}
                           height={window.innerHeight * (85 / 100)}
                           nodeAutoColorBy="type"
                           linkAutoColorBy="type"
                           d3AlphaDecay={0.2}
                           strokeWidth={2}
                           linkWidth={2}
                           nodeRelSize={this.state.forceGraphOpts.nodeRelSize}
                           enableNodeDrag={this.state.forceGraphOpts.enableNodeDrag} 
                           onLinkClick={this._handleLinkClick}
                           onNodeClick={this._handleNodeClick} />
  }
  _renderForceGraph2D () {
      return <ForceGraph2D id="forceGraph3D"
                           ref={el => { this.fg = el; }}
                           graphData={this.state.graph}
                           width={window.innerWidth}
                           height={window.innerHeight * (85 / 100)}
                           nodeAutoColorBy="type"
                           linkAutoColorBy="type"
                           d3AlphaDecay={0.2}
                           strokeWidth={2}
                           linkWidth={2}
                           nodeRelSize={this.state.forceGraphOpts.nodeRelSize}
                           enableNodeDrag={this.state.forceGraphOpts.enableNodeDrag} 
                           onLinkClick={this._handleLinkClick}
                           onNodeClick={this._handleNodeClick} />
  }
  _handleShowModal () {
    this.setState ({ showModal : true });
  }
  _handleCloseModal () {
    this.setState ({ showModal : false });
    this.setState ({ minLinkWeight : this.state.minLinkWeight });
  }
  _handleUpdateSettings (e) {
    var targetName = e.currentTarget.name;
    if (targetName === 'useCache') {
      var useCache = e.currentTarget.checked;
      console.log (useCache);
      this.setState ({ useCache : useCache });
      localStorage.setItem (targetName, JSON.stringify (useCache));
    } else if (targetName === 'visMode') {
      this.setState ({ visMode : e.currentTarget.value });
      localStorage.setItem (targetName, JSON.stringify(e.currentTarget.value));
    }
  }
  _renderModal () {
    return (
      <>
        <Modal show={this.state.showModal} onHide={this._handleCloseModal}>
          <Modal.Header closeButton>
            <Modal.Title>Settings</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <b>Visualization Mode</b> <br/>        
            <input type="radio" name="visMode" 
                   value="3D"
                   checked={this.state.visMode === "3D"} 
                   onChange={this._handleUpdateSettings} />3D  <br/>        
            <input type="radio" name="visMode" 
                   value="2D"
                   checked={this.state.visMode === "2D"} 
                   onChange={this._handleUpdateSettings} />2D <br/><br/>
            <b>Use Cache</b> <br/>
            <input type="checkbox" name="useCache"
                   checked={this.state.useCache}
                   onChange={this._handleUpdateSettings} /> Cache responses to queries. <br/><br/>
        <b>Minimum Link Weight</b> Current value: [{this.state.minLinkWeight / 100}]<br/>
            Include only links with a weight greater than this threshold.
            <Slider min={0} max={100} value={this.state.minLinkWeight} onChange={this._onMinLinkWeightChange} onAfterChange={this._onMinLinkWeightAfterChange} handle={handle} />
        
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={this._handleCloseModal}>
              Close
            </Button>
          </Modal.Footer>
        </Modal>
      </>
    );
  }
  /**
   * Handle events that can only occur once the component is mounted.
   */
  componentDidMount() {
    this._hydrateState ();
  }
  _renderTable () {
    var columns = [
      {
        Header: "Name",
        columns: [
          {
            Header: "First Name",
            accessor: "firstName"
          },
          {
          Header: "Last Name",
            id: "lastName",
            accessor: d => d.lastName
          }
        ]
      },
      {
        Header: "Info",
        columns: [
          {
            Header: "Age",
            accessor: "age"
          },
          {
            Header: "Status",
            accessor: "status"
          }
        ]
      },
      {
        Header: 'Stats',
        columns: [
          {
            Header: "Visits",
            accessor: "visits"
          }
        ]
      }
    ];
    var data = [
      { firstName : "Bob", lastName : "Smith", age : 10, status : "great" },
      { firstName : "Bob", lastName : "Smith", age : 10, status : "great" },
      { firstName : "Bob", lastName : "Smith", age : 10, status : "great" },
      { firstName : "Bob", lastName : "Smith", age : 10, status : "great" },
      { firstName : "Bob", lastName : "Smith", age : 10, status : "great" },
      { firstName : "Bob", lastName : "Smith", age : 10, status : "great" },
      { firstName : "Bob", lastName : "Smith", age : 10, status : "great" }
    ];
    return (
      <div className="tableView">
        <ReactTable
          data={data}
          columns={columns}
          defaultPageSize={10}
          className="-striped -highlight"
        />
      </div>
    );
  }
  /**
   * Render the component.
   */
  render0() {
    // Render it.
    return (
      <div className="App" id="AppElement">

      
      <SplitPane class="splitPane" split="horizontal">
        <div style={{ height : "80%" }}>

      
        <header className="App-header" style={{ height : "100%" }}> 
          <p>
            TranQL {this._renderModal () }
            <Button id="navModeButton"
                    outline className="App-control"
                    color="primary" onClick={this._setNavMode}>
              { this.state.navigateMode && this.state.visMode === '3D' ? "Navigate" : "Select" }
            </Button>
            <Button id="runButton"
                    outline className="App-control"
                    color="success" onClick={this._executeQuery}>
              Run
            </Button>
            <IoIosSettings id="settings" className="App-control" onClick={this._handleShowModal} />
        </p>
        </header>
      	  <CodeMirror ref={this._codemirror}
                      value={this.state.code}
                      onChange={this._updateCode}
                      onKeyUp={this.handleKeyUpEvent} 
                      options={this.state.codeMirrorOptions}
                      autoFocus={true} />
          { this._renderForceGraph () }

      
        </div>
        <div style={{ height: "20%" }}>

      
              { this._renderTable () }
              <div id="graph"></div>      
              <ReactJson id="info"
                 src={this.state.selectedNode}
                 theme="monokai" />
        </div>
      </SplitPane>
      </div>
    );
  }
  
  render() {
    // Render it.
    return (
      <div className="App" id="AppElement">
        <header className="App-header" > 
          <p>
            TranQL {this._renderModal () }
            <Button id="navModeButton"
                    outline className="App-control"
                    color="primary" onClick={this._setNavMode}>
              { this.state.navigateMode && this.state.visMode === '3D' ? "Navigate" : "Select" }
            </Button>
            <Button id="runButton"
                    outline className="App-control"
                    color="success" onClick={this._executeQuery}>
              Run
            </Button>
            <IoIosSettings id="settings" className="App-control" onClick={this._handleShowModal} />
          </p>
        </header>
        <div>
      	  <CodeMirror ref={this._codemirror}
                      value={this.state.code}
                      onChange={this._updateCode}
                      onKeyUp={this.handleKeyUpEvent} 
                      options={this.state.codeMirrorOptions}
                      autoFocus={true} />
          { this._renderForceGraph () }
          {/* this._renderTable () */}
          <div id="graph"></div>
          <div id="info">
            <ReactJson
              src={this.state.selectedNode}
              theme="monokai" />
          </div>
        </div>
      </div>
    );
  }
}

export default App;
