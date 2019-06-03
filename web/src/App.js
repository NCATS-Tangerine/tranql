import React, { Component } from 'react';
import { css } from '@emotion/core';
import { Button } from 'reactstrap';
import { Modal, Form } from 'react-bootstrap';
import { ForceGraph3D, ForceGraph2D, ForceGraphVR } from 'react-force-graph';
import * as THREE from 'three';
import ReactJson from 'react-json-view'
import JSONTree from 'react-json-tree';
import logo from './static/images/tranql.png'; // Tell Webpack this JS file uses this image
import { contextMenu } from 'react-contexify';
import { IoIosSwap, IoIosSettings, IoIosPlayCircle } from 'react-icons/io';
import { FaSearch, FaEye, FaPen, FaChartBar as FaBarChart, FaCircleNotch, FaSpinner, FaMousePointer, FaBan, FaArrowsAlt } from 'react-icons/fa';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import ReactTable from 'react-table';
import { Text as ChartText, ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, Legend as ChartLegend } from 'recharts';
import DefaultTooltipContent from 'recharts/lib/component/DefaultTooltipContent';
//import Tooltip from 'rc-tooltip';
import ReactTooltip from 'react-tooltip';
import Slider, { Range } from 'rc-slider';
import { GridLoader } from 'react-spinners';
import SplitPane from 'react-split-pane';
import Cache from './Cache.js';
import Actor from './Actor.js';
import AnswerViewer from './AnswerViewer.js';
import Legend from './Legend.js';
import { shadeColor, adjustTitle } from './Util.js';
import { Toolbar, Tool, ToolGroup } from './Toolbar.js';
import LinkExaminer from './LinkExaminer.js';
import Message from './Message.js';
import Chain from './Chain.js';
import ContextMenu from './ContextMenu.js';
import { RenderInit, LegendFilter, LinkFilter, NodeFilter, SourceDatabaseFilter, CurvatureAdjuster } from './Render.js';
import "react-tabs/style/react-tabs.css";
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

const spinnerStyleOverride = css`
    display: block;
    margin: 4 auto;
    border-color: red;
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
    if(process.env.NODE_ENV === 'development') {
      this.tranqlURL = "http://localhost:8001";
    }
    if(process.env.NODE_ENV === 'production') {
      this.tranqlURL = window.location.origin;
    }
    //this.tranqlURL = window.location.origin;
    //this.tranqlURL = "http://localhost:8001"; // dev only
    this.robokop_url = "https://robokop.renci.org";
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

    // Toolbar
    this._setNavMode = this._setNavMode.bind(this);
    this._setSelectMode = this._setSelectMode.bind(this);

    this._setHighlightTypesMode = this._setHighlightTypesMode.bind(this);
    this._highlightType = this._highlightType.bind(this);

    this._setConnectionExaminerActive = this._setConnectionExaminerActive.bind(this);

    // The visualization
    this._renderForceGraph = this._renderForceGraph.bind (this);
    this._renderForceGraph2D = this._renderForceGraph2D.bind (this);
    this._renderForceGraph3D = this._renderForceGraph3D.bind (this);
    this._renderForceGraphVR = this._renderForceGraphVR.bind (this);
    this._updateGraphElementVisibility = this._updateGraphElementVisibility.bind(this);
    this._updateFg = this._updateFg.bind(this);
    this._handleNodeClick = this._handleNodeClick.bind(this);
    this._handleNodeRightClick = this._handleNodeRightClick.bind(this);
    this._handleNodeHover = this._handleNodeHover.bind(this);
    this._fgAdjustCharge = this._fgAdjustCharge.bind(this);
    this._handleLinkClick = this._handleLinkClick.bind(this);
    this._handleLinkHover = this._handleLinkHover.bind(this);
    this._handleLinkRightClick = this._handleLinkRightClick.bind(this);
    this._handleContextMenu = this._handleContextMenu.bind(this);
    this._updateGraphSize = this._updateGraphSize.bind(this);
    this._updateGraphSplitPaneResize = this._updateGraphSplitPaneResize.bind(this);
    this._setSchemaViewerActive = this._setSchemaViewerActive.bind(this);

    // Fetch data for schema visualization
    this._getSchema = this._getSchema.bind(this);

    // Visualization filter state values
    this._onLinkWeightRangeChange = this._onLinkWeightRangeChange.bind (this);
    this._onNodeDegreeRangeChange = this._onNodeDegreeRangeChange.bind (this);
    this._onLegendDisplayLimitChange = this._onLegendDisplayLimitChange.bind (this);

    // Visualization modifiers
    this._onChargeChange = this._onChargeChange.bind (this);

    // Type chart
    this._renderTypeChart = this._renderTypeChart.bind (this);

    // Annotate graph
    this._annotateGraph = this._annotateGraph.bind (this);


    // Settings management
    this._handleShowModal = this._handleShowModal.bind (this);
    this._handleCloseModal = this._handleCloseModal.bind (this);
    this._handleUpdateSettings = this._handleUpdateSettings.bind (this);
    this._toggleCheckbox = this._toggleCheckbox.bind (this);
    this._renderCheckboxes = this._renderCheckboxes.bind (this);
    this._hydrateState = this._hydrateState.bind (this);

    this._handleShowAnswerViewer = this._handleShowAnswerViewer.bind (this);
    this._handleMessageDialog = this._handleMessageDialog.bind (this);
    this._analyzeAnswer = this._analyzeAnswer.bind (this);
    this._cacheWrite = this._cacheWrite.bind (this);
    this._cacheRead = this._cacheRead.bind (this);
    this._clearCache = this._clearCache.bind (this);

    // Component rendering.
    this.render = this.render.bind(this);

    // Create code mirror reference.
    this._codemirror = React.createRef ();
    this._contextMenu = React.createRef ();
    this._answerViewer = React.createRef ();
    this._messageDialog = React.createRef ();
    this._graphSplitPane = React.createRef ();


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
      record : null,
      message : null,
      messageRecord : null,
      graph : {
        nodes : [],
        links : [],

        // Types that aren't rendered
        hiddenTypes: {
          "nodes": [],
          "links": []
        },
        // Graph reference before being filtered to pass to the Legend component (filtered graph results in element types being omitted)
        typeMappings: {}
      },
      // Filters.
      linkWeightRange : [0, 100],
      nodeDegreeMax : 0,
      nodeDegreeRange : [0, 1000],
      legendRenderAmount : 10,
      dataSources : [],

      charge : -100,

      // Manage node selection and navigation.
      selectMode: true,
      selectedNode : {},
      selectedLink : {},
      contextNode : null,
      navigateMode: false,
      selectMode: false,

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
      colorGraph : true,
      forceGraphOpts : {
        nodeRelSize : 7,
        linkWidth: 2,
        enableNodeDrag : true
      },
      graphHeight : window.innerHeight,
      graphWidth : 0,
      curvedLinks : false, // Can't change the width of curved links beyond 0 due to it using THREE.Line
      directionalParticles : false, // Huge performance tank - basically unusable when viewing an entire graph
      directionalArrows : false, // Large performance loss when used with highlight types tool. Also looks ugly. Should be made into an option in settings.

      // Object viewer
      objectViewerEnabled : true,

      // Schema viewer
      schema : {
        nodes : [],
        links : [],

        // Types that aren't rendered
        hiddenTypes: {
          "nodes": [],
          "links": []
        },
        // Graph reference before being filtered to pass to the Legend component (filtered graph results in element types being omitted)
        typeMappings: {}
      },
      schemaMessage : null,
      schemaViewerActive : true,
      schemaViewerEnabled : true, // Sandbox the feature
      schemaLoaded : false,


      toolbarEnabled : true,

      connectionExaminer : false, // Connection examiner tool state

      highlightTypes : false, // Highlight types tool state
      highlightedType : [], // Currently highlighted types

      // Tools for the toolbar component
      tools: [
        <Tool name="Navigate" description="Click a node to move the camera to it and make it the center of rotation." callback={(bool) => this._setNavMode(bool)}>
        <FaArrowsAlt/>
        </Tool>,
        <Tool name="Select" description="Open a node or link in the object viewer" callback={(bool) => this._setSelectMode(bool)}>
          <FaMousePointer/>
        </Tool>,
        <Tool name="Highlight Types"
              description="Highlights all elements of the type that is being hovered over.<br/> Left click filters all of that type. Right click filters all not of that type."
              callback={(bool) => this._setHighlightTypesMode(bool)}>
          <FaSearch/>
        </Tool>,
        <Tool name="Examine Connection"
              description="Displays a connection between two nodes and all links between them"
              callback={(bool) => this._setConnectionExaminerActive(bool)}>
          <FaEye/>
        </Tool>
      ],
      buttons: [
        <IoIosPlayCircle data-tip="Answer Viewer - see each answer, its graph structure, links, knowledge source and literature provenance"
                         id="answerViewerToolbar"
                         className="App-control-toolbar ionic"
                         onClick={this._handleShowAnswerViewer} />,
        <IoIosSettings data-tip="Configure application settings" id="settingsToolbar" className="App-control-toolbar ionic" onClick={this._handleShowModal} />,
        <FaBarChart data-tip="Type Bar Chart - see all the types contained within the graph distributed in a bar chart"
                    className="App-control-toolbar fa"
                    onClick={() => this.setState ({ showTypeChart : true })} />,
        <FaPen className="App-control-toolbar fa" data-tip="Annotate Graph" onClick={() => this._annotateGraph ()}/>
      ],

      // Type chart
      showTypeNodes : true, // When false, shows link types (prevents far too many types being shown at once)
      showTypeChart : false,

      // Settings modal
      showSettingsModal : false,
      //showAnswerViewer : true
    };
    this._cache.read ('cache', this.state.code).
      then ((result) => {
        console.log ("-----------> ",result);
        if (result.length > 0) {
          this.setState ({
            record : result[0]
          });
        }
      });

    /**
     * Create the rendering pipeline, a chain of responsibility.
     */
    this._renderChain = new Chain ([
      new RenderInit (),
      new LinkFilter (),
      new NodeFilter (),
      new SourceDatabaseFilter (),
      new LegendFilter (),
      new CurvatureAdjuster ()
    ]);

    // Create rendering pipeline for schema
    this._schemaRenderChain = new Chain ([
      new RenderInit (),
      new NodeFilter (),
      new LegendFilter (),
      new CurvatureAdjuster ()
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
        console.log (" setting " + key + " => " + value);
        // parse the localStorage string and setState
        try {
          value = JSON.parse(value);
          this.setState({ [key]: value });
        } catch (e) {
          // handle empty string.
          console.log (" setting " + key + " => " + value);
          this.setState({ [key]: value });
        }
        console.log (" set " + this.state[key]);
      }
    }
    this._updateCode (this.state.code);
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
   * Sets the active force graph
   *
   * @private
   */
  _setSchemaViewerActive (active) {
    // Don't set state, thereby reloading the graph, if the schema viewer isn't enabled

    this.setState({ selectedNode : {}, schemaViewerActive : active }, () => {
      this._fgAdjustCharge (this.state.charge);
    });
    if (this.state.objectViewerEnabled) {
      let width = this._graphSplitPane.current.splitPane.offsetWidth;
      this._graphSplitPane.current.setState({ draggedSize : width, pane1Size : width , position : width });
      this._updateGraphSize(width);
    }

  }
  /**
   * Highlight or unhighlight a given node or link type
   *
   * @param {string|string[]} - Type/Types which are highlighted or unhighlighted
   * @param {boolean} highlight - Determines whether the nodes/links of the type will be highlighted or unhighlighted
   *
   * @private
   */
  _highlightType (type, highlight) {
    if (!Array.isArray(type)) {
      type = [type];
    }

    let graph = this.state.schemaViewerActive && this.state.schemaViewerEnabled ? this.state.schema : this.state.graph;
    const vMode = this.state.visMode;
    type.forEach(highlightType => {
      for (let graphElementType of ["nodes","links"]) {
        let elements = graph[graphElementType];
        for (let i=0;i<elements.length;i++) {
          let element = elements[i];
          let types = element.type;
          if (!Array.isArray(types)) types = [types];
          if (types.includes(highlightType)) {
            let obj = (element.__lineObj || element.__threeObj); //THREE.Mesh;
            let material;
            if (vMode !== "2D") {
              if (obj === undefined) return;
              material = obj.material; // : THREE.MeshLambertMaterial
            }
            let color;
            let opacity;
            if (highlight) {
              color = new THREE.Color(0xff0000);
              if (vMode !== "2D") {
                element.prevOpacity = material.opacity;
              }
              else {
                element.prevColor = element.color;
              }
              opacity = 1;
            }
            else {
              if (vMode !== "2D") {
                color = new THREE.Color(parseInt(element.color.slice(1),16));
                opacity = element.prevOpacity;
                delete element.prevOpacity;
              }
              else {
                color = new THREE.Color(parseInt(element.prevColor.slice(1),16));
                delete element.color;
              }
            }

            // console.log("Set",types.join(),"to",color.getHexString(),opacity || "undefined");
            if (vMode === "2D") {
              element.color = "#" + color.getHexString();
              // element.__indexColor = color.getHexString();

            }
            else {
              material.color = color;
              // Opacity will sometimes be undefined (happens when right click) because it is reloading the force graph.
              if (opacity !== undefined) material.opacity = opacity;
              // Stores reference to material that is reused on every object - setting this thousands of times is a serious performance tank because it seems like it rerenders the mesh everytime
              break;
            }
          }
        };
      }
    });
  }
  /**
   * Set the state of the connection examiner tool. Resets the selected node when toggled.
   *
   * @param {boolean} bool - Sets whether the tool is becoming active or not
   *
   * @private
   */
  _setConnectionExaminerActive(bool) {
    this.setState({ selectedNode: {}, connectionExaminer: bool });
  }
  /**
   * Set the state of the highlight types tool and let it clean up when it is turned off
   *
   * @param {boolean} bool - Sets whether or not the highlight types tool is active
   *
   * @private
   */
  _setHighlightTypesMode (bool) {
    if (!bool && this.state.highlightedType.length > 0) {
      this._highlightType(this.state.highlightedType, false);
    }
    this.setState({ highlightTypes : bool, highlightedType : [] });
  }
  /**
   * Set if the select mode tool is active.
   *
   * @param {boolean} select - Sets if active or not.
   * @private
   */
  _setSelectMode (select) {
    let width = this._graphSplitPane.current.splitPane.offsetWidth;
    if (this.state.objectViewerEnabled) {
      this._graphSplitPane.current.setState({ draggedSize : width, pane1Size : width , position : width });
    }
    this._updateGraphSize(width);
    this.setState ({
      selectMode: select,
      selectedNode: {},
      selectedLink: {}
    });
  }
  /**
   * Set if the navigation mode tool is active.
   *
   * @param {boolean} navigate - Sets if active or not.
   * @private
   */
  _setNavMode (navigate) {
    let width = this._graphSplitPane.current.splitPane.offsetWidth;
    if (this.state.objectViewerEnabled) {
      this._graphSplitPane.current.setState({ draggedSize : width, pane1Size : width , position : width });
    }
    this._updateGraphSize(width);
    this.setState ({
      navigateMode: navigate,
      selectedNode: {},
      selectedLink: {}
    });
  }
  /**
   * Render interface for depth analysis of an answer.
   *
   * @param {message} - A KGS message object to analyze.
   * @private
   */
  _analyzeAnswer (message) {
    // If we've already created the answer, use that.

    if (this.state.record && this.state.record.data && this.state.record.data.hasOwnProperty ("viewURL")) {
      var url = this.state.record.data.viewURL;
      console.log ('--cached-view-url: ' + url);
      this._answerViewer.current.handleShow (url);
      //var win = window.open (url, 'answerViewer');
      //win.focus ();
      return;
    }
    // Get it.
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
          result = result.replace(/"/g, '');
          var url = this.robokop_url + "/simple/view/" + result;
          console.log ('--new ' + url);
          message.viewURL = url;
          this._cacheWrite (message);
          this._answerViewer.current.handleShow (url);
          //var win = window.open (message.viewURL, 'answerViewer');
          //win.focus ();
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
    // Clear the visualization so it's obvious that data from the last query is gone
    // and we're fetching new data for the current query.
    this.setState ({
      graph : {
        nodes : [],
        links : [],

        hiddenTypes: {
          "nodes": [],
          "links": []
        },
        typeMappings: {}
      },
      selectedNode: {},
      selectedLink: {},

    });
    // Automatically switch from schema to graph view when query is run
    this._setSchemaViewerActive (false);

    let width = this._graphSplitPane.current.splitPane.offsetWidth;
    if (this.state.objectViewerEnabled) {
      this._graphSplitPane.current.setState({ draggedSize : width, pane1Size : width , position : width });
    }
    this._updateGraphSize(width);
    //localStorage.setItem ("code", JSON.stringify (this.state.code));
    // First check if it's in the cache.
    //var cachePromise = this._cache.read (this.state.code);
    var cachePromise = this.state.useCache ? this._cache.read ('cache', this.state.code) : Promise.resolve ([]);
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
                if (result.message) {
                  this._handleMessageDialog ("Error", result.message, result.details);
                  console.log ("--error: " + result.message);
                  this.setState ({
                    loading : false,
                    error : result.message
                  });
                } else {
                  /* Convert the knowledge graph to a renderable form. */
                  if (result.answers) {
                    // answers is not kgs 0.9 compliant. ... longer story.
                    delete result.answers;
                  }
                  this._translateGraph (result);
                  this._configureMessage (result);
                  this._cacheWrite (result);
                  this._setSchemaViewerActive(false);
                }
              },
              // Note: it's important to handle errors here
              // instead of a catch() block so that we don't swallow
              // exceptions from actual bugs in components.
              (error) => {
                this._handleMessageDialog ("Error", error.message, error.details);
                this.setState ({
                  loading : false,
                  error : error
                });
              }
            );
        }
      }.bind(this),
      function error (result) {
        this._handleMessageDialog ("Error", result.message, result.details);
        //console.log ("-- error", result);
      }.bind(this));
  }
  _cacheWrite (message) {
    //this._cache.write (this.state.code, result);
    var obj = {
      'key' : this.state.code,
      'data' : message
    };
    if (this.state.record) {
      obj.id = this.state.record.id;
    }
    console.log (obj);
    var record = this._cache.
        write ('cache', obj).
        then ((result) => {
          this._cache.get ('cache', result,
                           (result) => {
                             this.setState ({
                               loading : false,
                               record : result
                             })
                           })
        }).catch ((error) => {
          this.setState ({
            error
          })
        });
  }
  _configureMessageLogic (message) {
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
    return [dataSources,nodeDegrees];
  }
  _configureMessage (message) {
    console.log(message);
    if (message && message.knowledge_graph) {
      // Configure node degree range.
      let [dataSources, nodeDegrees] = this._configureMessageLogic(message);
      this.setState({
        dataSources : dataSources,
        message : message,
        nodeDegreeMax : nodeDegrees[0],
        nodeDegreeRange : [ 0, nodeDegrees[0] ]
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
    var message = message ? message : this.state.message;
    if (message) {
      this._renderChain.handle (message, this.state);
      this.setState({
        graph: message.graph
      });
    }
  }
  /**
   * Fetch the schema data for visualization
   *
   * @private
   */
   _getSchema () {
     this.setState(p => ({}),() => {
       var cachePromise = this.state.useCache ? this._cache.get ('schema', 0) : Promise.resolve (undefined);
       cachePromise.then (
         function success (result) {
           if (result !== undefined) {
             console.log("Got schema from cache");
             let msg = result.data;
             this._schemaRenderChain.handle (msg, this.state);
             this.setState({ schemaLoaded : true, schema : msg.graph, schemaMessage: msg });
             this.state.schemaViewerActive && this._setSchemaViewerActive(true);
           } else {
             fetch(this.tranqlURL + '/tranql/schema', {
               method: "GET"
             })
             .then((res) => res.json())
             .then(
               (result) => {
                 if (result.message) {
                   this._handleMessageDialog ("Error", result.message, result.details);
                   console.log ("--error: " + result.message);
                 } else {
                   if (result.answers) {
                     delete result.answers;
                   }

                   result.knowledge_graph = {
                     nodes: result.knowledge_graph.nodes.map((node) => {
                       return {
                         id: node,
                         type: node,
                         name: node
                       }
                     }),
                     edges: result.knowledge_graph.edges.reduce((acc, edge) => {
                       // TODO fix? Can't draw edges from a node to itself
                       if (edge[0] !== edge[1]) {
                         acc.push({
                           source_id: edge[0],
                           target_id: edge[1],
                           type: edge[2],
                           weight: 1
                         });
                       }
                       return acc;
                     }, [])
                  };

                   console.log("Fetched schema:", result);

                   this._schemaRenderChain.handle (result, this.state);

                   this.setState({ schemaLoaded : true, schema : result.graph, schemaMessage : result });
                   this.state.schemaViewerActive && this._setSchemaViewerActive(true);

                   this._cache.write ('schema', {
                     'id' : 0,
                     'data' : result
                   });
                 }
               }
             );
           }
         }.bind(this),
         function error (result) {
           this._handleMessageDialog ("Error", result.message, result.details);
         }.bind(this));
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
   * Handle a hover over a graph node
   *
   * @param {object} node - The node that is being hovered over in the graph
   * @param {object} prevNode - The node that was previously being hovered over in the graph
   *
   * @private
   */
  _handleNodeHover (node, prevNode) {
    if (this.state.highlightTypes) {
      let newType = [];
      if (prevNode !== null) {
        this._highlightType(prevNode.type, false);
      }
      if (node !== null) {
        this._highlightType(node.type, true);
        newType = node.type;
      }
      this.setState({ highlightedType : newType });
    }
  }
  /**
   * Handle a hover over a graph link
   *
   * @param {object} link - The link that is being hovered over in the graph
   * @param {object} prevLink - The link that was previously being hovered over in the graph
   *
   * @private
   */
  _handleLinkHover (link, prevLink) {
    if (this.state.highlightTypes) {
      let newType = [];
      // Eliminate overhead by not deselecting all the types if going to reselect them immediately after
      // If new link is null don't bother trying to check
      if (prevLink !== null && (link === null || JSON.stringify(prevLink.type) !== JSON.stringify(link.type))) {
        if (true || !(prevLink.source === link.target && prevLink.target === link.source) || (prevLink.source === link.source && prevLink.target === link.target)) {
          this._highlightType(prevLink.type, false);
        }
        // If the source and targets are synonymous don't unhighlight.
      }
      // Same goes for here but with the previous link
      // We still want to set newType though
      if (link !== null) {
        if (prevLink === null || JSON.stringify(prevLink.type) !== JSON.stringify(link.type)) {
          this._highlightType(link.type, true);
        }
        newType = link.type;
      }
      this.setState({ highlightedType : newType });
    }
  }
  /**
   * Handle a click on a graph link.
   *
   * @param {object} - A link in the force directed graph visualization.
   * @private
   */
  _handleLinkClick (link) {
    if (this.state.connectionExaminer) {
      this.setState({ selectedNode : (link === null ? null : { link : link }) });
    }
    else if (this.state.highlightTypes) {
      link !== null && this._updateGraphElementVisibility("links", link.type, true);
    }
    else if (link !== null &&
        this.state.selectedLink !== null &&
//        this.state.selectedLink.source !== link.source_id &&
//        this.state.selectedLink.target !== link.target_id &&
        this.state.selectMode &&
        !this.state.selectMode)
    {
      // Select the node.
      this.setState ((prevState, props) => ({
        selectedNode : { link : link.origin }
      }));
      let width = this._graphSplitPane.current.splitPane.offsetWidth * (1/2);
      if (this.state.objectViewerEnabled) {
        this._graphSplitPane.current.setState({ draggedSize : width, pane1Size : width , position : width });
      }
      this._updateGraphSize(width);
    }
  }
  _handleLinkRightClick (link) {
    if (this.state.highlightTypes && link !== null) {
      let linkType = Array.isArray(link.type) ? link.type : [link.type];
      let mappings;
      if (this.state.schemaViewerEnabled && this.state.schemaViewerActive) {
        mappings = this.state.schema.typeMappings.links;
      }
      else {
        mappings = this.state.graph.typeMappings.links;
      }
      if (mappings !== undefined) {
        let hideTypes = Object.keys(mappings).filter(t => !linkType.includes(t));
        this._updateGraphElementVisibility("links", hideTypes, true);
      }
    }
  }
  _handleNodeRightClick (node) {
    if (this.state.highlightTypes && node !== null) {
      let nodeType = Array.isArray(node.type) ? node.type : [node.type];
      let mappings;
      if (this.state.schemaViewerEnabled && this.state.schemaViewerActive) {
        mappings = this.state.schema.typeMappings.nodes;
      }
      else {
        mappings = this.state.graph.typeMappings.nodes;
      }
      if (mappings !== undefined) {
        let hideTypes = Object.keys(mappings).filter(t => !nodeType.includes(t));
        this._updateGraphElementVisibility("nodes", hideTypes, true);
      }
    }
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
   * Update graph size on split pane resize
   *
   * @private
   */
   _updateGraphSplitPaneResize () {
     this._updateGraphSize (this._graphSplitPane.current.pane1.offsetWidth);
   }

 /**
  * Update graph size
  *
  * @param {number} width - New width of the graph
  * @private
  */
  _updateGraphSize (width) {
    this.setState (prevState => ({ graphWidth: width, graphHeight: this.state.graphHeight }));
  }

  /**
   * Update fg when it is changed or rerendered
   *
   * @private
   */
  _updateFg () {
  }
  /**
   * Handle Legend callback on toggling of element type
   *
   * @param {string} graphElementType - Graph element type ("nodes" or "links")
   * @param {string|string[]} type - Type of element (e.g. "gene" or "affects_response_to")
   * @param {boolean} hidden - Determines the new visibility of the elements
   * @private
   */
  _updateGraphElementVisibility(graphElementType, type, hidden) {
    let graph = JSON.parse(JSON.stringify(this.state.schemaViewerEnabled && this.state.schemaViewerActive ? this.state.schema : this.state.graph));
    if (!Array.isArray(type)) type = [type];

    if (hidden) {
      graph.hiddenTypes[graphElementType].push(...type);
    } else {
      type.forEach(t => {
        graph.hiddenTypes[graphElementType].splice(graph.hiddenTypes[graphElementType].indexOf(t),1);
      });
    }

    if (this.state.schemaViewerEnabled && this.state.schemaViewerActive) {
      let newMessage = this.state.schemaMessage;
      newMessage.hiddenTypes = graph.hiddenTypes;
      this._schemaRenderChain.handle(newMessage, this.state);
      // console.log(message);
      this.setState({ schema : newMessage.graph });
    }
    else {
      let newMessage = this.state.message;
      newMessage.hiddenTypes = graph.hiddenTypes;

      this.setState({ message : newMessage }, () => {
        this._translateGraph();
      });
    }
  }

  /**
   * Handle a click on a graph node.
   *
   * @param {object} - A node in the force directed graph visualization.
   * @private
   */
  _handleNodeClick (node) {
    console.log (node);
    if (this.state.highlightTypes) {
      node !== null && this._updateGraphElementVisibility("nodes", node.type, true);
    }
    else if (this.state.navigateMode && this.state.visMode === '3D') {
      // Navigate camera to selected node.
      // Aim at node from outside it
      const distance = 40;
      const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
      this.fg.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, // new position
        node, // lookAt ({ x, y, z })
        3000  // ms transition duration
      );
    } else if (this.state.selectMode && node !== null && node.id !== undefined && node.id !== null &&
               this.state.selectedNode !== null &&
               this.state.selectedNode.id !== node.id &&
               this.state.selectMode)
    {
      // Select the node.
      this.setState ((prevState, props) => ({
        selectedNode : { node: node.origin }
      }));
      let width = this._graphSplitPane.current.splitPane.offsetWidth * (1/2);
      if (this.state.objectViewerEnabled) {
        this._graphSplitPane.current.setState({ draggedSize : width, pane1Size : width , position : width });
      }
      this._updateGraphSize(width);

    }
  }
  /**
   * Adjust the charge force on the current graph. Lower charges result in more spread out graphs.
   *
   * @param {number} charge - The new charge of the force graph
   *
   * @private
   */
  _fgAdjustCharge (charge) {
    if (this.fg) {
      this.fg.d3Force ('charge').strength(charge);
      this.fg.refresh ();
    }
  }
  /**
   * Render the force directed graph in either 2D or 3D rendering modes.
   * @param {Object} data - Data containing nodes and links that is used to render the force graph
   * @param {Object} props - Override default props used to render the graph.
   *
   * @private
   */
  _renderForceGraph (data, props) {
    var result = null;
    let defaultProps = {
      graphData:data,
       width:this.state.graphWidth,
       height:this.state.graphHeight,
       linkAutoColorBy:"type",
       nodeAutoColorBy:"type",
       d3AlphaDecay:0.2,
       strokeWidth:10,
       linkWidth:2,
       linkLabel: (l) => l.concatName,
       nodeRelSize:this.state.forceGraphOpts.nodeRelSize,
       enableNodeDrag:this.state.forceGraphOpts.enableNodeDrag,
       onLinkClick:this._handleLinkClick,
       onLinkHover:this._handleLinkHover,
       onLinkRightClick:this._handleLinkRightClick,
       onNodeRightClick:this._handleNodeRightClick,
       onNodeClick:this._handleNodeClick,
       onNodeHover:this._handleNodeHover
    };
    props = {
      ...defaultProps,
      ...props
    }
    if (this.state.curvedLinks && (this.state.visMode === '3D' || this.state.visMode === 'VR')) {
      // 2D not supported
      props = {
        ...props,
        linkCurvature:"curvature",
        linkCurveRotation:"rotation",
        linkWidth:undefined
      };
    }
    if (this.state.directionalParticles) {
      props = {
        ...props,
        linkDirectionalParticles: 5,
        linkDirectionalParticleResolution: 1 // Helps with performance
      };
    }
    if (this.state.directionalArrows) {
      props = {
        ...props,
        linkDirectionalArrowLength: 10,
        linkDirectionalArrowColor: (link) => link.color,
        linkDirectionalArrowRelPos: 1
      };
    }
    if (this.state.visMode === '3D') {
      result = this._renderForceGraph3D (data, props);
    } else if (this.state.visMode === '2D') {
      result = this._renderForceGraph2D (data, props);
    } else if (this.state.visMode === 'VR') {
      result = this._renderForceGraphVR (data, props);
    } else {
      throw "Unrecognized rendering mode: " + this.state.visMode;
    }
    return result;
  }
  /**
   * Render in 3D
   *
   * @private
   * nodeAutoColorBy="type"
   */
  _renderForceGraph3D (data, props) {
      return <ForceGraph3D {...props} />
  }
  /**
   * Render in 3D
   *
   * @private
   */
  _renderForceGraph2D (data, props) {
      return <ForceGraph2D {...props} />
  }

  /**
   * Render in VR
   *
   * @private
   */
  _renderForceGraphVR (data, props) {
      return <ForceGraphVR {...props} />
  }
  /**
   * Show the modal settings dialog.
   *
   * @private
   */
  _handleShowModal () {
    this.setState ({ showSettingsModal : true });
  }
  _handleShowAnswerViewer () {
    console.log (this._answerViewer);
    if (this.state.message) {
      var message = this.state.message;
      this._analyzeAnswer({
        "question_graph"  : message.question_graph,
        "knowledge_graph" : message.knowledge_graph,
        "answers"         : message.knowledge_map
      });
    }
  }
  _handleMessageDialog (title, message, details) {
    this._messageDialog.current.handleShow (title, message, details === undefined ? "" : details);
  }
  /**
   * Take appropriate actions on the closing of the modal settings dialog.
   *
   * @private
   */
  _handleCloseModal () {
    this.setState ({ showSettingsModal : false });
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
      this.setState ({ visMode : e.currentTarget.value }, () => {
        this._fgAdjustCharge (this.state.charge);
      });
      localStorage.setItem (targetName, JSON.stringify(e.currentTarget.value));
    } else if (targetName === 'colorGraph') {
      var colorGraph = e.currentTarget.checked;
      this.setState ({ colorGraph : colorGraph });
      localStorage.setItem (targetName, JSON.stringify (colorGraph));
      this._translateGraph ();
    }
  }
  _toggleCheckbox(index) {
    const checkboxes = this.state.dataSources;
    checkboxes[index].checked = !checkboxes[index].checked;
    this.setState({
      checkboxes : checkboxes
    });
    this._translateGraph ();
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
   *
   * @private
   */
  _onChargeChange (event)  {
    let value = event.target.value;
    this.setState({ charge : value });
    value !== "" && this._fgAdjustCharge (value);
    localStorage.setItem ("charge", JSON.stringify (value));
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
    this._translateGraph ();
  }
  /**
   * Respond to changing the node degree range.
   *
   * @param {object} value - New range.
   * @private
   */
  _onNodeDegreeRangeChange (value) {
    this.setState({ nodeDegreeRange : value});
    this._translateGraph ();
    localStorage.setItem ("minNodeDegree", JSON.stringify (value));
  }
  /**
   * Respond to changing the value of legend display Limit
   * @param {number} value - The new legend display Limit
   * @private
   */
  _onLegendDisplayLimitChange (event) {
    let value = event.target.value;
    value !== "" && this.setState({ legendRenderAmount : value });
  }
  /**
   * Send graph message to backplane which annotates it and relays it back
   *
   * @private
   */
  _annotateGraph () {
    if (this.state.message === null) {
      console.log("Can't annotate message if graph isn't loaded");
      return;
    }
    let message = Object.assign({}, this.state.message);
    delete message.graph;
    delete message.hiddenTypes;
    /*
      Structure of Message object in schema is:
        type: object
        required:
          - question_graph
          - knowledge_graph
          - knowledge_maps
      So delete the useless information (graph is huge and contains a lot of data that slows the requests down)
    */
    this.setState({ loading : true });
    fetch(this.tranqlURL + '/tranql/annotate', {
      method: "POST",
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify (message)
    }).then(res => res.json())
      .then(
        (result) => {
          if (result.message) {
            this._handleMessageDialog ("Error", result.message, result.details);
            console.log ("--error: " + result.message);
            this.setState ({
              loading : false,
              error : result.message
            });
          } else {
            for (let type in result.knowledge_graph) {
              result.knowledge_graph[type].forEach(newElem => {
                newElem.source_database = [];
              });
            }
            // for (let type in result.knowledge_graph) {
            //   result.knowledge_graph[type].forEach(newElem => {
            //     message.knowledge_graph[type].forEach(oldElem => {
            //       if (newElem.id === oldElem.id) {
            //         for (let prop in newElem) {
            //           oldElem[prop] = newElem[prop];
            //         }
            //       }
            //     });
            //   });
            // }
            this.setState({ loading : false });
            console.log("Annotated result:", result);
            console.log("Current message:", message);
            this._translateGraph (result);
            this._configureMessage (result);
            this._setSchemaViewerActive(false);
          }
        },
        (error) => {
          this.setState({
            error : error,
            loading : false
          });
        }
      );
  }
  /**
   * Render the type bar chart
   *
   * @private
   */
  _renderTypeChart () {
    const renderAmount = 9;
    let graph = this.state.schemaViewerActive && this.state.schemaViewerEnabled ? this.state.schema : this.state.graph;
    let mappings = Legend.sortMappings(graph.typeMappings, renderAmount, renderAmount);
    if (!mappings.hasOwnProperty('nodes')) mappings.nodes = [];
    if (!mappings.hasOwnProperty('links')) mappings.links = [];
    let data = (this.state.showTypeNodes ? mappings.nodes : mappings.links).map(elem => (
      {
        type: adjustTitle(elem.type),
        // A little confusing...
        "Filtered Quantity": elem.hasOwnProperty('actualQuantity') ? elem.actualQuantity : 0,
        "Actual Quantity": elem.quantity,
        color: elem.color,
        hidden: elem.hasOwnProperty('actualQuantity') ? false : true
      }
    ));
    return (
      <Modal show={this.state.showTypeChart}
             onHide={() => this.setState ({ showTypeChart : false })}
             dialogClassName="typeChart">
        <Modal.Header closeButton>
          <Modal.Title id="typeChartTitle">
            {this.state.showTypeNodes ? 'Node' : 'Link'} Bar Graph
            <IoIosSwap id="swapBar" onClick={() => this.setState({ showTypeNodes: !this.state.showTypeNodes })}/>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <ResponsiveContainer width={"100%"} height={"100%"}>
            <BarChart data={data}
                      margin={{
                        top: 5,
                        right: 30,
                        left: 20,
                        bottom: 5
                      }}
                      barCategoryGap={10}>
              <CartesianGrid strokeDasharray="3 3"/>
              <XAxis dataKey="type"
                     height={85}
                     interval={0}
                     tickMargin={0}
                     tick={(props) => {
                       const width = props.width/props.visibleTicksCount;
                       return (
                         <g transform={`translate(${props.x},${props.y})`}>
                           <switch>
                              {/* Translate x -50% of width to center it*/}
                              <foreignObject style={{transform:`translateX(-${width/2}px)`}} x={0} y={0} dy={16} width={width} height="100%">
                                <p style={{padding:"2px",fontSize:"14px",textAlign:"center"}} xmlns="http://www.w3.org/1999/xhtml">{props.payload.value}</p>
                              </foreignObject>
                            </switch>
                            {/*
                              props.payload.value.split(/((?:\w+\s+){1,5})/).map((block, i) => (
                                <text x={0} y={0} dy={16+(i*16)} textAnchor="end" fill="#666" font-size="14px" transform="rotate(-35)">
                                  {block}
                                </text>
                              ))
                            */}
                           </g>
                       );
                     }}
              />
              <YAxis />
              <ChartTooltip content={
                (props) => {
                  /*const newPayload = props.payload !== null && props.payload.length > 0
                    ? [
                        {
                          name: 'Filtered quantity',
                          value: props.payload[0].payload.filtered
                        },
                        ...props.payload
                      ]
                    : [

                      ];
                  */
                  const newPayload = props.payload;

                  const label = props.payload !== null && props.payload.length > 0
                    ? props.payload[0].payload.type + (props.payload[0].payload.hidden
                      ? " (hidden)"
                      : "")
                    : ""

                  return (<DefaultTooltipContent {...props} label={label} payload={newPayload}/>);
                }
              }
              />
              <Bar dataKey="Actual Quantity">
                {
                  data.map((entry, index) => {
                    let color = entry.color;
                    return <Cell key={index} fill={color} />
                  })
                }
              </Bar>
              <Bar dataKey="Filtered Quantity">
                {
                  data.map((entry, index) => {
                    let color = entry.color;
                    return <Cell key={index} fill={shadeColor(color,-20)} />
                  })
                }
              </Bar>
              {/*<Bar dataKey="Filtered Quantity" fill="#7fc1ff" />*/}
            </BarChart>
          </ResponsiveContainer>
        </Modal.Body>
      </Modal>
    );
  }
  /**
   * Render the modal settings dialog.
   *
   * @private
   */
  _renderModal () {
    return (
      <>
        <Modal show={this.state.showSettingsModal}
               onHide={this._handleCloseModal}>
          <Modal.Header closeButton>
            <Modal.Title>Settings</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <Tabs>
              <TabList>
                <Tab><b>General</b></Tab>
                <Tab><b>Graph Structure</b></Tab>
                <Tab><b>Knowledge Sources</b></Tab>
              </TabList>
              <TabPanel>
            <b>Visualization Mode and Graph Colorization</b> <br/>

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
                   onChange={this._handleUpdateSettings} />VR &nbsp;&nbsp;
            <input type="checkbox" name="colorGraph"
                   checked={this.state.colorGraph}
                   onChange={this._handleUpdateSettings} /> Color the graph.
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
              </TabPanel>
              <TabPanel>
            <br/>
            <b>Link Weight Range</b> Min: [{this.state.linkWeightRange[0] / 100}] Max: [{this.state.linkWeightRange[1] / 100}]<br/>
            Include only links with a weight in this range.
            <Range allowCross={false} defaultValue={this.state.linkWeightRange} onChange={this._onLinkWeightRangeChange} />

            <b>Node Connectivity Range</b> Min: [{this.state.nodeDegreeRange[0]}] Max: [{this.state.nodeDegreeRange[1]}] (reset on load)<br/>
            Include only nodes with a number of connections in this range.
            <Range allowCross={false}
                   defaultValue={this.state.nodeDegreeRange}
                   onChange={this._onNodeDegreeRangeChange}
                   max={this.state.nodeDegreeMax}/>
            <br/>
            <b>Force Graph Charge</b><br/>
            Set the charge force on the active graph<br/>
            <Form>
              <Form.Control
              type="number"
              defaultValue={this.state.charge}
              onChange={this._onChargeChange}
              onKeyDown={(e) => {if (e.keyCode === 13) e.preventDefault();}}
              />
            </Form>

            <b>Legend Display Limit</b><br/>
            Set number of node and link types that legend displays<br/>
            <Form>
              <Form.Control
              type="number"
              defaultValue={this.state.legendRenderAmount}
              onChange={this._onLegendDisplayLimitChange}
              onKeyDown={(e) => {if (e.keyCode === 13) e.preventDefault();}}
              />
            </Form>


            {/*<div className={"divider"}/>*/}
            <br/>
              </TabPanel>
              <TabPanel>
            <b>Sources</b> Filter graph edges by source database. Deselecting a database deletes all associations from that source.
            {this._renderCheckboxes()}
              </TabPanel>
            </Tabs>
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

    // Populate concepts and relations metadata.
    this._getModelConcepts ();
    this._getModelRelations ();

    // Fetch schema
    this._getSchema ();

    this._updateGraphSize(document.body.offsetWidth);
  }

  render() {
    // Render it.
    return (
      <div className="App" id="AppElement">
      {this._renderModal () }
      {this._renderTypeChart ()}
        <ReactTooltip place="left"/>
        <header className="App-header" >
          <div id="headerContainer">
            <p style={{display:"inline-block",flex:1}}>TranQL</p>
            <AnswerViewer show={true} ref={this._answerViewer} />
            <Message show={false} ref={this._messageDialog} />
            <GridLoader
              css={spinnerStyleOverride}
              id={"spinner"}
              sizeUnit={"px"}
              size={6}
              color={'#2cbc12'}
              loading={this.state.loading && (this.state.schemaViewerActive || !this.state.schemaViewerEnabled)} />
            {
              !this.state.toolbarEnabled &&
                <Button id="navModeButton"
                        outline
                        color="primary" onClick={() => {this._setNavMode(!this.state.navigateMode); this._setSelectMode(!this.state.selectMode)}}>
                  { this.state.navigateMode && (this.state.visMode === '3D' || this.state.visMode === '2D') ? "Navigate" : "Select" }
                </Button>
            }
            <Button id="runButton"
                    outline
                    color="success" onClick={this._executeQuery}>
              Run
            </Button>
            <div id="appControlContainer" style={{display:(this.state.toolbarEnabled ? "none" : "")}}>
              <IoIosSettings data-tip="Configure application settings" id="settings" className="App-control" onClick={this._handleShowModal} />
              <IoIosPlayCircle data-tip="Answer Viewer - see each answer, its graph structure, links, knowledge source and literature provenance" id="answerViewer" className="App-control" onClick={this._handleShowAnswerViewer} />
            </div>
          </div>
        </header>
        <div>
      	  <CodeMirror ref={this._codemirror}
                      value={this.state.code}
                      onChange={this._updateCode}
                      onKeyUp={this.handleKeyUpEvent}
                      options={this.state.codeMirrorOptions}
                      autoFocus={true} />
          <Legend typeMappings={this.state.graph.typeMappings}
                  hiddenTypes={this.state.graph.hiddenTypes}
                  nodeTypeRenderAmount={this.state.legendRenderAmount}
                  linkTypeRenderAmount={this.state.legendRenderAmount}
                  callback={this._updateGraphElementVisibility}
                  render={(!this.state.schemaViewerActive || !this.state.schemaViewerEnabled) && this.state.colorGraph}/>
          <Legend typeMappings={this.state.schema.typeMappings}
                  hiddenTypes={this.state.schema.hiddenTypes}
                  nodeTypeRenderAmount={this.state.legendRenderAmount}
                  linkTypeRenderAmount={this.state.legendRenderAmount}
                  callback={this._updateGraphElementVisibility}
                  render={this.state.schemaViewerActive && this.state.schemaViewerEnabled && this.state.colorGraph}/>
          <div id="graph"></div>
          <div id="viewContainer">
            {
              this.state.toolbarEnabled && (
                <Toolbar id="toolbar" default={0} tools={this.state.tools} buttons={this.state.buttons}/>
              )
            }
            {
              /* Don't bother rendering split pane if the object viewer isn't enabled. Causes resize issues. */
              <SplitPane split="vertical"
                         defaultSize={this.state.graphWidth}
                         minSize={0}
                         allowResize={this.state.objectViewerEnabled && (this.state.selectedNode === null || Object.keys(this.state.selectedNode).length !== 0)}
                         maxSize={document.body.clientWidth}
                         style={{"backgroundColor":"black","position":"static"}}
                         ref={this._graphSplitPane}
                         onDragFinished={(width) => this._updateGraphSplitPaneResize()}
              >
                <div>
                  <div id="schemaBanner" style={{display:(this.state.schemaViewerEnabled ? "" : "none")}}>
                  {((this.state.schemaViewerActive && !this.state.schemaLoaded) || (!this.state.schemaViewerActive && this.state.loading)) &&  <FaSpinner style={{marginRight:"10px"}} className="fa-spin"/>}
                  {this.state.schemaViewerActive ? "Schema:" : "Graph:"}
                    <div id="schemaViewToggleButtonContainer">
                      <Button color="primary"
                              id="schemaViewToggleButton"
                              outline
                              size="sm"
                              onClick={(e) => this._setSchemaViewerActive (!this.state.schemaViewerActive)}
                      >
                      {this.state.schemaViewerActive ? "Show graph" : "Show schema"}
                      </Button>
                    </div>
                  </div>
                  <div onContextMenu={this._handleContextMenu}>
                    <LinkExaminer link={this.state.selectedNode}
                                  render={this.state.connectionExaminer && this.state.selectedNode !== null && this.state.selectedNode.hasOwnProperty('link')}/>
                    {this.state.schemaViewerActive && this.state.schemaViewerEnabled ?
                      (
                        this._renderForceGraph (
                          this.state.schema,
                          {
                          ref: (el) => {if (this.state.schemaViewerActive) this.fg = el; this._updateFg ()},

                          // Kind of hacky - in essense, every time the active graph changes, the d3 alpha decay forces are reapplied.
                          // This detects if this is the first render and, if so, it allows the alpha decay forces to be applied to the graph.
                          // Additionally, the react-force-graph does not seem to like it when you pass in a property as undefined.
                          // Therefore, the spread operator is used here to conditionally add properties to the object without having to pass in a property as undefined
                          // Commented out because it breaks charge. Needs to somehow reset graph when graph type changes, but also needs to retain auto color property.
                          // ...(this.state.schema.nodes.some(n => n.index !== undefined) || this.state.schema.links.some(l => l.index !== undefined) ? {d3AlphaDecay: 1} : {})
                        })
                      )
                    :
                      (
                        this._renderForceGraph (
                          this.state.graph, {
                          ref: (el) => {if (!this.state.schemaViewerActive) this.fg = el; this._updateFg ()}

                          // Refer to similar block in the above schema graph for a reference to what atrocious things are occuring here
                          // ...(this.state.graph.nodes.some(n => n.index !== undefined) || this.state.graph.links.some(l => l.index !== undefined) ? {d3AlphaDecay: 1} : {})
                        })
                      )
                    }
                    <ContextMenu id={this._contextMenuId} ref={this._contextMenu}/>
                  </div>
                </div>
                <div id="info" style={!this.state.objectViewerEnabled ? {display:"none"} : {}}>
                  <JSONTree
                  shouldExpandNode={(key,data,level) => level === 1}
                  hideRoot={true}
                  theme={
                    {scheme:"monokai", author:"wimer hazenberg (http://www.monokai.nl)", base00:"#272822",base01:"#383830",base02:"#49483e",base03:"#75715e",base04:"#a59f85",
                    base05:"#f8f8f2",base06:"#f5f4f1",base07:"#f9f8f5", base08:"#f92672",base09:"#fd971f",base0A:"#f4bf75",base0B:"#a6e22e",base0C:"#a1efe4",base0D:"#66d9ef",
                    base0E:"#ae81ff",base0F:"#cc6633"}
                  }
                  invertTheme={false}
                  data={this.state.selectedNode} />
                </div>

              </SplitPane>
            }
          </div>
        </div>
        <div id='next'/>
      </div>
    );
  }
}

export default App;
