import React, { Component } from 'react';
import { css } from '@emotion/core';
import { Button } from 'reactstrap';
import { Modal } from 'react-bootstrap';
import { ForceGraph3D, ForceGraph2D, ForceGraphVR } from 'react-force-graph';
import ReactJson from 'react-json-view'
import logo from './static/images/tranql.png'; // Tell Webpack this JS file uses this image
//import { IoIosSettings, IoIosPlayCircle, IoIosNavigate } from 'react-icons/io';
import { IoIosSettings } from 'react-icons/io';
import ReactTable from "react-table";
import Tooltip from 'rc-tooltip';
import Slider, { Range } from 'rc-slider';
import { GridLoader } from 'react-spinners';
import SplitPane from 'react-split-pane';
import Cache from './Cache.js';
import Actor from './Actor.js';
import Chain from './Chain.js';
import { RenderInit, LinkFilter, NodeFilter, SourceDatabaseFilter } from './Render.js';
import { Menu, Item, Separator, Submenu, MenuProvider, contextMenu } from 'react-contexify';
import 'react-contexify/dist/ReactContexify.min.css';
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

String.prototype.unquoted = function (){return this.replace (/(^")|("$)/g, '')}
Array.prototype.unique = function() {
  return this.filter(function (value, index, self) { 
    return self.indexOf(value) === index;
  });
};

class ContextMenu extends Component {
  constructor(props) {
    /* Create state elements and initialize configuration. */
    super(props);
    this._handleClick = this._handleClick.bind (this);
    this._menu = React.createRef ();
  }
  _handleClick = (e) => {
    console.log(e);
  }
  render () {
    return (
        <Menu id={this.props.id}>
          <Item>Copy</Item>
          <Separator />
          <Item>Paste</Item>
          <Item>Cut</Item>
          <Separator />
          <Submenu label="Foobar">
            <Item onClick={this._handleClick}>Foo</Item>
            <Item onClick={this._handleClick}>Bar</Item>
          </Submenu>
        </Menu>
    );
  }
}

function openInNewTab(url) {
  var win = window.open(url, '_blank');
  win.focus();
}

const spinnerStyleOverride = css`
    display: block;
    margin: 4 auto;
    border-color: red;
    position: absolute;
    right: 186px;
    top: 9px;
`;

/** 
 * @desc The main TranQL application class.
 * Integrates the query editor, query executor, rendering pipeline, and visualization.
 * @author Steve Cox scox@renci.org
 */
class App extends Component {
  /**
   * A TranQL web app.
   */
  constructor(props) {
    /* Create state elements and initialize configuration. */
    super(props);
    this.tranqlURL = window.location.origin; 
    this.tranqlURL = "http://localhost:8001";
    this.robokop_url = "http://robokop.renci.org";
    this.contextMenuId = "contextMenuId";
    
    // Query editor support.
    this._getConfiguration = this._getConfiguration.bind (this);
    this._getModelConcepts = this._getModelConcepts.bind (this);
    this._getModelRelations = this._getModelRelations.bind (this);
    this._codeAutoComplete = this._codeAutoComplete.bind(this);
    this._updateCode = this._updateCode.bind (this);
    this._executeQuery = this._executeQuery.bind(this);
    this._configureMessage = this._configureMessage.bind (this);
    this._translateGraph = this._translateGraph.bind (this);

    // The visualization
    this._setNavMode = this._setNavMode.bind(this);
    this._renderForceGraph = this._renderForceGraph.bind (this);
    this._renderForceGraph2D = this._renderForceGraph2D.bind (this);
    this._renderForceGraph3D = this._renderForceGraph3D.bind (this);
    this._renderForceGraphVR = this._renderForceGraphVR.bind (this);
    this._handleNodeClick = this._handleNodeClick.bind(this);
    this._handleNodeRightClick = this._handleNodeRightClick.bind(this);
    this._handleLinkClick = this._handleLinkClick.bind(this);
    this._handleContextMenu = this._handleContextMenu.bind(this);

    // Visualization filter state values
    this._onLinkWeightRangeChange = this._onLinkWeightRangeChange.bind (this);
    this._onNodeDegreeRangeChange = this._onNodeDegreeRangeChange.bind (this);

    // Settings management
    this._handleShowModal = this._handleShowModal.bind (this);
    this._handleCloseModal = this._handleCloseModal.bind (this);    
    this._handleUpdateSettings = this._handleUpdateSettings.bind (this);
    this._toggleCheckbox = this._toggleCheckbox.bind (this);
    this._renderCheckboxes = this._renderCheckboxes.bind (this);
    this._hydrateState = this._hydrateState.bind (this);

    this._analyzeAnswer = this._analyzeAnswer.bind (this);
    this._cacheRead = this._cacheRead.bind (this);
    this._clearCache = this._clearCache.bind (this);

    // Component rendering.
    this.render = this.render.bind(this);

    // Create code mirror reference.
    this._codemirror = React.createRef ();
    this._contextMenu = React.createRef ();
    
    // Cache graphs locally using IndexedDB web component.
    this._cache = new Cache ();

    // Configure initial state.
    this.state = {
      code : "select chemical_substance->gene->disease\n  from \"/graph/gamma/quick\"\n where disease=\"asthma\"",

      // Concept model concepts and relations.
      modelConcepts : [],
      modelRelations : [],
      
      // The graph; populated when a query's executed.
      loading: false,
      message : null,
      graph : {
        nodes : [],
        links : []
      },
      // Filters.
      linkWeightRange : [0, 100],
      nodeDegreeMax : 0,
      nodeDegreeRange : [0, 1000],
      dataSources : [],
      
      // Manage node selection and navigation.
      selectMode: true,
      selectedNode : {},
      selectedLink : {},
      contextNode : null,
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

    /**
     * Create the rendering pipeline, a chain of responsibility.
     */
    this._renderChain = new Chain ([
      new RenderInit (),
      new LinkFilter (),
      new NodeFilter (),
      new SourceDatabaseFilter ()
    ]);
  }
  /**
   * Restore component state from persistent storage on initialization.
   *
   * @private
   */
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
  /**
   * Read an object from the cache.
   *
   * @param {string} key - The object's unique key.
   * @private
   */
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
   * Clear the cache.
   *
   * @private
   */
  _clearCache () {
    this._cache.clear ();
  }
  /**
   * Callback for the query editor to set the value of the code.
   *
   * @param {string} newCode - New value of the query in the editor.
   * @private
   */
  _updateCode (newCode) {
    this.setState({
      code: newCode
    });
  }
  /**
   * Callback for handling autocompletion within the query editor.
   *
   * @param {object} cm - The CodeMirror object.
   * @private
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
   *
   * @private
   */
  _setNavMode () {
    if (! this.state.navigateMode) {
      // Turn off the object viewer if we're going into navigate.
      document.getElementById ('info').style.display = 'none';
    }
    this.setState ({
      navigateMode: ! this.state.navigateMode
    });
  }
  /**
   * Render interface for depth analysis of an answer.
   *
   * @param {message} - A KGS message object to analyze.
   * @private
   */
  _analyzeAnswer (message) {
    // We didn't find it in the cache. Run the query.
    fetch(this.robokop_url + '/api/simple/view', {
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
          var url = "http://robokop.renci.org/simple/view/" + result.unquoted ();
          console.log ("--simple view url: ", url);
          openInNewTab (url);
          message.viewURL = url;
          //this._cache.write (this.state.code, message);
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
   * Checks for the requested object in cache.
   * If not present, executes query and receives a KGS message object.
   *    Passes the message to the rendering pipeline.
   *    Writes the messge to cache.
   *
   * @private
   */
  _executeQuery () {
    console.log ("--query: ", this.state.code);
    // First check if it's in the cache.
    //var cachePromise = this._cache.read (this.state.code);
    var cachePromise = this.state.useCache ? this._cache.read (this.state.code) : Promise.resolve ([]);
    cachePromise.then (
      function success (result) {
        if (result.length > 0) {
          // Translate the knowledge graph given current settings.
          this._translateGraph (result[0].data)
          this._configureMessage (result[0].data)
        } else {
          // We didn't find it in the cache. Run the query.
          this.setState ({
            loading : true
          });
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
                if (result.answers) {
                  // answers is not kgs 0.9 compliant.
                  delete result.answers;
                }
                //this._analyzeAnswer (result);
                this._translateGraph (result);
                this._configureMessage (result);
                this._cache.write (this.state.code, result);
                //console.log ("new tab: " + result);
                this.setState ({
                  loading : false
                });
              },
              // Note: it's important to handle errors here
              // instead of a catch() block so that we don't swallow
              // exceptions from actual bugs in components.
              (error) => {
                this.setState ({
                  loading : false
                });
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

/*

select chemical_substance->gene->disease
  from "/graph/gamma/quick"
 where disease="MONDO:0010940"

  select disease->chemical_substance
  from "/graph/gamma/quick"
  where disease="MONDO:0005180"
*/
  
  _configureMessage (message) {
    if (message && message.knowledge_graph) {
      // Configure node degree range.
      var nodeDegrees = message.knowledge_graph.nodes.map ((node, index) => {
        return message.knowledge_graph.edges.reduce ((acc, cur) => {
          return cur.target_id === node.id ? acc + 1 : acc;
        }, 1);
      }).sort ((a,b) => a - b).reverse();
      // Configure data sources
      var dataSources = message.knowledge_graph.edges.flatMap ((edge, index) => {
        return edge.source_database;
      }).unique ().flatMap ((source, index) => {
        var result = [];
        if (typeof source == "string") {
          result.push ({ checked : true, label : source });
        } else if (typeof source == "array") {
          result = source.map ((s, index) => {           
            return { checked : true, label : s };
          });
        }
        return result;
      });
      this.setState({
        dataSources : dataSources,
        message : message,
        nodeDegreeMax : nodeDegrees[0], //message.graph.nodes.length,
        nodeDegreeRange : [ 0, nodeDegrees[0] ] //message.graph.nodes.length ]
      });
    }
  }
  /**
   * Render the graph via the rendering pipeline.
   *
   * @param {message} - A KGS message object.
   * @private
   */
  _translateGraph (message) {
    this._renderChain.handle (message, this.state);
    this.setState({
      graph: message.graph
    });
  }
  /**
   * Get the configuration for this deployment.
   *
   * @private
   */
  _getConfiguration () {
    fetch(this.tranqlURL + '/tranql/configuration', {
      method: "POST",
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify ({
      })
    }).then(res => res.json())
      .then(
        (result) => {
          this.setState({
            configuration : result
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
   * Get the concept model and stores as state.
   *
   * @private
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
   * Get the concept model relations and stores as state.
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
  /**
   * Handle a click on a graph link.
   *
   * @param {object} - A link in the force directed graph visualization.
   * @private
   */
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
  _handleNodeRightClick (node) {
    this.setState ({
      contextNode : node
    });
  }
  _handleContextMenu (e) {    
    e.preventDefault();
    contextMenu.show({
      id: this._contextMenuId,
      event: e,
      props: {
        foo: 'bar'
      }
    });
  }

  /**
   * Handle a click on a graph node.
   *
   * @param {object} - A node in the force directed graph visualization.
   * @private
   */
  _handleNodeClick (node) {
    console.log (node);
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
  /**
   * Render the force directed graph in either 2D or 3D rendering modes.
   *
   * @private
   */
  _renderForceGraph () {
    var result = null;
    if (this.state.visMode === '3D') {
      result = this._renderForceGraph3D ();
    } else if (this.state.visMode === '2D') {
      result = this._renderForceGraph2D ();
    } else if (this.state.visMode === 'VR') {
      result = this._renderForceGraphVR ();
    } else {
      throw "Unrecognized rendering mode: " + this.state.visMode;
    }
    return result;
  }
  /**
   * Render in 3D
   *
   * @private
   */
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
                           onNodeRightClick={this._handleNodeRightClick}
                           onNodeClick={this._handleNodeClick} />
  }
  /**
   * Render in 3D
   *
   * @private
   */
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
                           onNodeRightClick={this._handleNodeRightClick}
                           onNodeClick={this._handleNodeClick} />
  }

  /**
   * Render in VR
   *
   * @private
   */
  _renderForceGraphVR () {
      return <ForceGraphVR id="forceGraphVR"
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
                           onNodeRightClick={this._handleNodeRightClick}
                           onNodeClick={this._handleNodeClick} />
  }
  /**
   * Show the modal settings dialog.
   *
   * @private
   */
  _handleShowModal () {
    this.setState ({ showModal : true });
  }
  /**
   * Take appropriate actions on the closing of the modal settings dialog.
   *
   * @private
   */
  _handleCloseModal () {
    this.setState ({ showModal : false });
    //this.setState ({ linkWeightRange : this.state.linkWeightRange});
  }
  /**
   * Handle updated settings from the modal settings dialog.
   *
   * @param {object} - An update event. Its currentTarget element designates the selected component.
   * @private
   */
  _handleUpdateSettings (e) {
    var targetName = e.currentTarget.name;
    console.log ("--update settings: " + targetName);
    if (targetName === 'useCache') {
      // Specifies if the cache should be engaged or not.
      var useCache = e.currentTarget.checked;
      console.log (useCache);
      this.setState ({ useCache : useCache });
      localStorage.setItem (targetName, JSON.stringify (useCache));
    } else if (targetName === 'visMode') {
      // Toggle between 2D and 3D visualizations.
      this.setState ({ visMode : e.currentTarget.value });
      localStorage.setItem (targetName, JSON.stringify(e.currentTarget.value));
    }
  }
  _toggleCheckbox(index) {
    const checkboxes = this.state.dataSources;    
    checkboxes[index].checked = !checkboxes[index].checked;
    this.setState({
      checkboxes : checkboxes
    });
    this._translateGraph (this.state.message);
  }
  _renderCheckboxes() {
    const checkboxes = this.state.dataSources;
    return checkboxes.map((checkbox, index) =>
            <div key={index}>
                <label>
                    <input
                        type="checkbox"
                        checked={checkbox.checked}
                        onChange={this._toggleCheckbox.bind(this, index)}
                    />
                    {checkbox.label}
                </label>
            </div>
        );
  }
  /**
   * Respond to changing range of link weights.
   *
   * @param {number} value - The new link weight range.
   * @private
   */
  _onLinkWeightRangeChange (value) {
    this.setState({ linkWeightRange : value});
    localStorage.setItem ("linkWeightRange", JSON.stringify (value));
    this._translateGraph (this.state.message);
  }
  /**
   * Respond to changing the node degree range.
   *
   * @param {object} value - New range.
   * @private
   */
  _onNodeDegreeRangeChange (value) {
    this.setState({ nodeDegreeRange : value});
    this._translateGraph (this.state.message);
    localStorage.setItem ("minNodeDegree", JSON.stringify (value));
  }
  /**
   * Render the modal settings dialog.
   *
   * @private
   */
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
                   onChange={this._handleUpdateSettings} />3D &nbsp;
            <input type="radio" name="visMode" 
                   value="2D"
                   checked={this.state.visMode === "2D"} 
                   onChange={this._handleUpdateSettings} />2D &nbsp;
            <input type="radio" name="visMode" 
                   value="VR"
                   checked={this.state.visMode === "VR"} 
                   onChange={this._handleUpdateSettings} />VR
            <br/>
            <div className={"divider"}/>
            <br/>
        
            <b>Use Cache</b> <br/>
            <input type="checkbox" name="useCache"
                   checked={this.state.useCache}
                   onChange={this._handleUpdateSettings} /> Use cached responses.
            <Button id="clearCache"
                    outline className="App-control"
                    color="primary" onClick={this._clearCache}>
              Clear the cache
            </Button>
            <br/>
            <br/>
            <div className={"divider"}/>
            <br/>
            <b>Link Weight Range</b> Min [{this.state.linkWeightRange[0] / 100} Max: [{this.state.linkWeightRange[1] / 100}]<br/>
            Include only links with a weight in this range.
            <Range allowCross={false} defaultValue={this.state.linkWeightRange} onChange={this._onLinkWeightRangeChange} />

            <b>Node Connectivity</b> Min: [{this.state.nodeDegreeRange[0]}] Max: [{this.state.nodeDegreeRange[1]}] (reset on load)<br/>
            Include only nodes with a number of connections in this range.
            <Range allowCross={false}
                   defaultValue={this.state.nodeDegreeRange}
                   onChange={this._onNodeDegreeRangeChange}
                   max={this.state.nodeDegreeMax}/>
            <br/>
            <div className={"divider"}/>
            <br/>
            <b>Sources</b> Filter graph edges by source database. Deselecting a database will delete all associations from that source.
            {this._renderCheckboxes()}
                                          
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
   *
   * @private
   */
  componentDidMount() {
    this._hydrateState ();
  }
  
  render() {
    // Render it.
    return (
      <div className="App" id="AppElement">
        <header className="App-header" > 
          <div>
            TranQL {this._renderModal () }
            <GridLoader
              css={spinnerStyleOverride}
              id={"spinner"}
              sizeUnit={"px"}
              size={6}
              color={'#2cbc12'}
              loading={this.state.loading} />
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
          </div>
        </header>
        <div>
      	  <CodeMirror ref={this._codemirror}
                      value={this.state.code}
                      onChange={this._updateCode}
                      onKeyUp={this.handleKeyUpEvent} 
                      options={this.state.codeMirrorOptions}
                      autoFocus={true} />
          <div onContextMenu={this._handleContextMenu}>
            { this._renderForceGraph () }
            <ContextMenu id={this._contextMenuId} ref={this._contextMenu}/>
          </div>
          <div id="graph"></div>
          <div id="info">
            <ReactJson
              src={this.state.selectedNode}
              theme="monokai" />
          </div>
        </div>
        <div id='next'/>
      </div>
    );
  }
    
}

export default App;
