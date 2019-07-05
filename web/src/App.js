import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import { css } from '@emotion/core';
import Dexie from 'dexie';
import { Button } from 'reactstrap';
import { Modal, Form, Card, Container, Row, Col, ListGroup, Tab as BsTab, Navbar } from 'react-bootstrap';
import { ForceGraph3D, ForceGraph2D, ForceGraphVR } from 'react-force-graph';
import ReactJson from 'react-json-view'
import JSONTree from 'react-json-tree';
import logo from './static/images/tranql.png'; // Tell Webpack this JS file uses this image
import { contextMenu } from 'react-contexify';
import { IoIosArrowDropupCircle, IoIosArrowDropdownCircle, IoIosSwap, IoIosPlayCircle } from 'react-icons/io';
import {
  FaCog, FaDatabase, FaQuestionCircle, FaSearch, FaHighlighter, FaEye, FaPen,
  FaChartBar as FaBarChart, FaCircleNotch, FaSpinner, FaMousePointer,
  FaBan, FaArrowsAlt, FaTrash, FaEdit, FaPlayCircle
} from 'react-icons/fa';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-confirm-alert/src/react-confirm-alert.css';
import ReactTable from 'react-table';
import { Text as ChartText, ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, Legend as ChartLegend } from 'recharts';
import InlineEdit from 'react-edit-inline2';
import DefaultTooltipContent from 'recharts/lib/component/DefaultTooltipContent';
//import Tooltip from 'rc-tooltip';
import ReactTooltip from 'react-tooltip';
import Slider, { Range } from 'rc-slider';
import { GridLoader } from 'react-spinners';
import SplitPane from 'react-split-pane';
import Cache from './Cache.js';
import Actor from './Actor.js';
import AnswerViewer from './AnswerViewer.js';
import QueriesModal from './QueriesModal.js';
import confirmAlert from './confirmAlert.js';
import Legend from './Legend.js';
import highlightTypes from './highlightTypes.js';
import { shadeColor, adjustTitle, debounce, scrollIntoView } from './Util.js';
import { Toolbar, Tool, ToolGroup } from './Toolbar.js';
import LinkExaminer from './LinkExaminer.js';
import FindTool from './FindTool.js';
import Message from './Message.js';
import Chain from './Chain.js';
import ContextMenu from './ContextMenu.js';
import { RenderInit, RenderSchemaInit, IdFilter, LegendFilter, LinkFilter, NodeFilter, SourceDatabaseFilter, CurvatureAdjuster } from './Render.js';
import "react-tabs/style/react-tabs.css";
import 'rc-slider/assets/index.css';
import "react-table/react-table.css";
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import { Controlled as CodeMirror } from 'react-codemirror2';
require('create-react-class');
require('codemirror/lib/codemirror.css');
require('codemirror/mode/sql/sql');

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
    this.__highlightTypes = highlightTypes.bind(this);

    this._setConnectionExaminerActive = this._setConnectionExaminerActive.bind(this);

    // The visualization
    this._renderForceGraph = this._renderForceGraph.bind (this);
    this._renderForceGraph2D = this._renderForceGraph2D.bind (this);
    this._renderForceGraph3D = this._renderForceGraph3D.bind (this);
    this._renderForceGraphVR = this._renderForceGraphVR.bind (this);
    this._updateGraphElementVisibility = this._updateGraphElementVisibility.bind(this);
    this._legendButtonRightClick = this._legendButtonRightClick.bind(this);
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

    // Help modal
    this._renderHelpModal = this._renderHelpModal.bind (this);
    this._renderToolbarHelpModal = this._renderToolbarHelpModal.bind (this);


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
    this._updateCacheViewer = this._updateCacheViewer.bind (this);

    // Component rendering.
    this.render = this.render.bind(this);
    this._updateDimensions = this._updateDimensions.bind(this);

    // Create code mirror references.
    this._codemirror = React.createRef ();
    this._contextMenu = React.createRef ();

    // Create modal references
    this._answerViewer = React.createRef ();
    this._messageDialog = React.createRef ();
    this._exampleQueriesModal = React.createRef ();
    this._cachedQueriesModal = React.createRef ();

    // Create the graph's GUI-related references
    this._graphSplitPane = React.createRef ();
    this._toolbar = React.createRef ();
    this._findTool = React.createRef ();


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
      schemaLegendRenderAmount : {
        nodes: 20,
        links: 10
      },
      queryLegendRenderAmount : {
        nodes: 10,
        links: 10
      },
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
      showCodeMirror : true,

      // Configure the 3d force directed graph visualization.
      visMode : '3D',
      useCache : true,
      cachedQueries : [],
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
      tools : [
        <Tool name="Navigate" shortcut="v" description="Click a node to move the camera to it and make it the center of rotation." callback={(bool) => this._setNavMode(bool)}>
        <FaArrowsAlt/>
        </Tool>,
        <Tool name="Select" shortcut="g" description="Open a node or link in the object viewer" callback={(bool) => this._setSelectMode(bool)}>
          <FaMousePointer/>
        </Tool>,
        <Tool name="Highlight Types"
              shortcut="h"
              description="Highlights all elements of the type that is being hovered over.<br/> Left click filters all of that type. Right click filters all not of that type."
              callback={(bool) => this._setHighlightTypesMode(bool)}>
          <FaHighlighter/>
        </Tool>,
        <Tool name="Examine Connection"
              shortcut="f"
              description="Displays a connection between two nodes and all links between them"
              callback={(bool) => this._setConnectionExaminerActive(bool)}>
          <FaEye/>
        </Tool>
      ],
      buttons : [
        <FaPlayCircle data-tip="Answer Navigator - see each answer, its graph structure, links, knowledge source and literature provenance"
                         id="answerViewerToolbar"
                         className="App-control-toolbar fa"
                         onClick={this._handleShowAnswerViewer} />,
        <FaSearch data-tip="Find tool - helps to quickly locate specific things in the graph" id="findTool" className="App-control-toolbar fa" onClick={() => this._findTool.current.show()}/>,
        <FaQuestionCircle data-tip="Help & Information" id="helpButton" className="App-control-toolbar fa" onClick={() => this.setState({ showHelpModal : true })}/>,
        <FaDatabase data-tip="Cache Viewer - search through previous queries" id="cachedQueriesButton" className="App-control-toolbar fa" onClick={() => this._cachedQueriesModal.current.show()}/>,
        <FaCog data-tip="Configure application settings" id="settingsToolbar" className="App-control-toolbar fa" onClick={this._handleShowModal} />,
        // Perfectly functional but does not provide enough functionality as of now to warrant its presence
        /*<FaBarChart data-tip="Type Bar Chart - see all the types contained within the graph distributed in a bar chart"
                    className="App-control-toolbar fa"
                    onClick={() => this.setState ({ showTypeChart : true })} />,*/
        // The tool works as intended but the annotator does not yet.
        /*<FaPen className="App-control-toolbar fa" data-tip="Annotate Graph" onClick={() => this._annotateGraph ()}/>*/
      ],
      toolHelpDescriptions : {
        tools : [
          {
            title: "Navigate",
            description: `
            This tool is intended to make navigating the force graph more easy to do. Left clicking a node will pan the camera to it and zoom in on it.
            It will also make it the center of rotation for the camera.
            Left clicking and holding a node will not trigger this tool and will instead drag the node like normal.
            Right clicking and dragging will shift the center of rotation away from the node selected with this tool.`
          },
          {
            title: "Select",
            description: `
            This tool allows you to view the additional data that nodes and links may possess. To use it, left click a node or link, which will bring up the object viewer.
            From there, you can navigate the tree view of the selected object and view all the properties that it has.`
          },
          {
            title: "Highlight Types",
            description: `
            This tool allows you to highlight all the nodes or links that share a type. It will highlight the type of the node or link that the cursor is currently hovering over.
            For nodes and links of multiple types, it will highlight all other nodes or links that share any types with it.
            Left clicking a node or link with this tool will hide all highlighted elements. Right clicking a node or link with this tool will hide all non-highlighted elements.`
          },
          {
            title: "Examine Connection",
            description: `
            This tool allows you to view all links, and the direction of each link, existing betweeen two nodes.
            To use the tool, left click any link between a pair of desired nodes.
            This will bring up the connection viewer interface.
            It will display each node's name as an abbreviation. It also colors codes their names according to the node's color in the force graph.
            If you forget a node's name, you can hover over the abbreviation, and it will display its name in full.
            `
          }
        ],
        buttons: [
          {
            title: "Answer Navigator",
            description: "This button brings up Robokop's depth analysis of the answer. It also displays a variety of other data related to the graph."
          },
          {
            title: "Find Tool",
            description: (
              <div>
                <div className="section">
                  <h6>Introduction:</h6>
                  <p>
                    This button brings up the find tool, which can also be opened with the keyboard shortcut control+F (the normal browser find tool can be opened with F3).
                  The find tool enables the user to use JSON-like attribute selectors to find certain objects in the graph.
                  </p>
                </div>
                <div className="section">
                  <h6>Structure:</h6>
                  <p>
                    The general structure of queries is `selector`{"{`attributes`}"}. A selector can be either "nodes", "links", or "*". The asterisk selector selects both nodes and links.
                    You can also connect these selectors with transitions, with the structure `selector`{"{`attributes`}"} -> `selector`{"{`attributes`}"} -> `selector`{"{`attributes`}"}. Note: only links are applicable in the second selector.
                    The `{"{}"}` following the selector may be omitted if no attributes are present.
                    Attributes must be valid <a target="_blank" href="https://tools.ietf.org/html/rfc7159">JSON</a>. This means that attributes are structured as key to value, where key is an attribute that a node or link may or may not possess.
                    If you are unsure as to what attributes nodes and links have, you can use the <FaMousePointer style={{fontSize:"14px"}}/> select tool to view a node or link's attributes.
                    However, keep in mind, only some attributes such as "id", "name", "type", and "equivalent_identifiers" are standard. Not all nodes or links are gaurenteeed to have others.
                  </p>
                  <div className="section">
                    <h6>Flags:</h6>
                    <p>
                      A colon in an attribute key indicates that the following text is an attribute flag. Attribute flags modify the behavior of how the attribute is compared to the provided value.
                      For example, if an attribute is a list ("['a','b','c']"), you can use the `includes` flag to check if `a` is in the list. This would look like "nodes{`{"attribute:includes" : "a"}`}".
                      All normal colons inside of attribute keys must be escaped, i.e. preceded by a backslash ("\:"), or it will be assumed that the following text is an attribute flag.
                    </p>
                    <div className="section">
                      <h6>The valid flags are:</h6>
                      <Row>
                        <dl>
                          <Col><dt>regex</dt></Col><Col><dd>Matches a <a target="_blank" href="http://cecas.clemson.edu/~warner/M865/RegexBasics.html">regular expression</a> against the element's attribute<br/><a href="javascript:void(0)" onClick={
                            ()=>scrollIntoView("#regexFlag")
                          }>Example</a></dd></Col>
                          <Col><dt>func</dt></Col><Col><dd>Evals a JavaScript function which is passed the element's attribute as the only argument. Should return true or false to indicate if the node should or should not be included.<br/><a href="javascript:void(0)" onClick={
                            ()=>scrollIntoView("#funcFlag")
                          }>Example</a></dd></Col>
                          <Col>
                            <dt>Special</dt>
                            <dd>
                              Any other method in the element's attribute's JavaScript prototype chain (for common references see&nbsp;
                              <a target="_blank" href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/prototype">Text</a> and&nbsp;
                              <a target="_blank" href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/prototype">Lists</a>).
                              <br/><a href="javascript:void(0)" onClick={
                                ()=>scrollIntoView("#regexFlag")
                              }>Example (list includes)</a>
                            </dd>
                          </Col>
                        </dl>
                      </Row>
                    </div>
                  </div>
                  <div className="section">
                    <h6>Magic variables (no current uses)</h6>
                    <p>
                      While flags are concerning attribute keys, magic variables are used in attribute values.
                      These variables use the syntax "__`variable name`__". They are used as if they are plain text, for example, "nodes->links{`{"type:regex":"foo|__sourceNodes__"}`}->nodes".
                      All instances of a normal two underscores in a row must be escaped with a backslash ("\__"), or it will result in any text following it and preceding another two unescaped underscores being detected as a magic variable.
                    </p>
                    <div className="section">
                      <h6>The valid magic variables are:</h6>
                      <Row>
                        <dl>
                          <Col><dt>__sourceNodes__</dt></Col><Col><dd>(Only applicable in the second selector of a nodes->links->nodes query) The value of __sourceNodes__ is a regex string that matches for any ids of the nodes from the source selector.</dd></Col>

                          <Col><dt>__targetNodes__</dt></Col><Col><dd>(Only applicable in the second selector of a nodes->links->nodes query) The value of __targetNodes__ is a regex string that matches for any ids of the nodes from the target selector.</dd></Col>

                          <Col><dt>__element__</dt></Col><Col><dd>The value of __element__ is the current element being tested for the attribute.</dd></Col>
                        </dl>
                      </Row>
                    </div>
                  </div>
                </div>
                <div className="section">
                  <h6>Example queries:</h6>
                  <Row>
                    <dl>
                      <Col><dt>nodes{`{"id": "chemical_substance"}`}</dt></Col>
                      <Col><dd>This will find all nodes in the graph whose `id` attribute equals "chemical_substance".</dd></Col>

                      <Col id="regexFlag"><dt>nodes{`{"equivalent_identifiers:includes":"CHEMBL:CHEMBL3"}`} -><br/> links{`{"type:includes":"related_to"}`} -><br/> nodes{`{"name:regex":"(disease|genetic_condition)"}`}</dt></Col>
                      <Col><dd>This will find all nodes in the graph who have the curie "CHEMBL:CHEMBL3" in their equivalent_identifiers attribute, all nodes whose name matches the regular expression "(disease|genetic_condition)",
                      and all links whose source is any node from the first selector, target is from the third selector, and has the type "related_to".</dd></Col>

                      <Col id="funcFlag"><dt>nodes{`{"description:func":"function(description) { return description.split("/").includes('test'); }"}`}</dt></Col>
                      <Col><dd>This will find all nodes in the graph whose `description` attribute split by a forward slash contains the string "test".</dd></Col>
                    </dl>
                  </Row>
                </div>
              </div>
          )
          },
          {
            title: "Help & Information",
            description: `
            This button brings up the help and information center, where you can find various references for using TranQL.`
          },
          {
            title: "Cache Viewer",
            description: `
            This button brings up the cache viewer interface, which displays all queries which have been locally cached.
            It allows for you to find previous queries and quickly view them, edit them, or delete them.`
          },
          {
            title: "Settings",
            description: `
            This button brings up the settings interface, which allows you to customize the behavior of TranQL.`
          }
        ]
      },

      // Type chart
      showTypeNodes : true, // When false, shows link types (prevents far too many types being shown at once)

      // Modals
      showSettingsModal : false,
      showTypeChart : false,
      // Cached queries modal
      cachedQueriesModalTools: [
        <FaTrash data-tip="Delete from the cache"
                 onClick={() => {
                   // this._cachedQueriesModal.current.hide();
                   confirmAlert({
                     title:"Delete cached query",
                     message:"Are you sure you want to delete this query?",
                     buttons:[
                       {
                         label: 'Confirm',
                         onClick: () => {
                           const currentQuery = this._cachedQueriesModal.current.currentQuery;
                           // The `id` property is the cache's id of the query.
                           this.state.cachedQueries = this.state.cachedQueries.filter((query) => query.id !== currentQuery.id);
                           this.setState({ cachedQueries : this.state.cachedQueries });
                           // Don't let the query go below 0
                           let newCurrentQueryIndex = Math.max(0, this._cachedQueriesModal.current.state.currentQueryIndex - 1);
                           this._cachedQueriesModal.current.setState({ currentQueryIndex : newCurrentQueryIndex });
                           this._cache.db.cache.delete(currentQuery.id);
                         }
                       },
                       {
                         label:'Cancel',
                         onClick: () => {}
                       }
                     ]
                   });
                 }}/>
      ],
      // Help modal
      showHelpModal : false,
      showToolbarHelpModal : false,
      toolbarHelpModalActiveType : 0,
      toolbarHelpModalActiveToolType : {
        buttons: 0,
        tools: 0
      },
      exampleQueries : [
          {
            title: 'Protein-Metabolite Interaction',
            query:
`-- What proteins are targetted by the metabolite KEGG:C00017?

set metabolite = "KEGG:C00017"

select metabolite->protein
  from "/graph/rtx"
 where metabolite=$metabolite

`
        },
        {
          title: 'Phenotypic Feature-Disease Association',
          query:
`-- What diseases are associated with the phenotypic feature HP:0005978?

select phenotypic_feature->disease
	from "/graph/rtx"
 where phenotypic_feature="HP:0005978"
`
        },
        {
          title: 'Drug-Disease Pair',
          query:
`--
-- Produce clinial outcome pathways for this drug disease pair.
--

set drug = 'PUBCHEM:2083'
set disease = 'MONDO:0004979'

select chemical_substance->gene->anatomical_entity->phenotypic_feature<-disease
  from '/graph/gamma/quick'
 where chemical_substance = $drug
   and disease = $disease`
        },
        {
          title: 'Drug Targets Gene',
          query:
`--
-- What drug targets some gene?
--

set target_gene = 'HGNC:6871' --mapk1
select chemical_substance->gene
  from '/graph/gamma/quick'
 where gene = $target_gene`
        },
        {
          title: 'Tissue-Disease Association',
          query:
`--
-- What tissue types are associated with [disease]?
--
set disease = 'asthma'
select disease->anatomical_feature->cell
  from '/graph/gamma/quick'
 where disease = $disease
`
        },
        {
          title: 'Workflow 5 v3',
          query:
`--
-- Workflow 5
--
--   Modules 1-4: Chemical Exposures by Clinical Clusters
--      For ICEES cohorts, eg, defined by differential population
--      density, which chemicals are associated with these
--      cohorts with a p_value lower than some threshold?
--
--   Modules 5-*: Knowledge Graph Phenotypic Associations
--      For chemicals produced by steps 1-4, what phenotypes are
--      associated with exposure to these chemicals?
--

SELECT population_of_individual_organisms->chemical_substance->gene->biological_process->phenotypic_feature
  FROM "/schema"
 WHERE icees.table = 'patient'
   AND icees.year = 2010
   AND icees.cohort_features.AgeStudyStart = '0-2'
   AND icees.feature.EstResidentialDensity < 1
   AND icees.maximum_p_value = 1
   AND drug_exposure !=~ '^(SCTID.*|rxcui.*|CAS.*|SMILES.*|umlscui.*)$'`
        }
      ]

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
     * We want to reset the interval if user highlights again. Stores `id`:`interval` Structure was too complicated so it is now separated into two objects.
     */
    this._highlightTypeFadeIntervals = {
    };
    this._highlightTypeFadeTimeouts = {
    };

    /**
     * Create the rendering pipeline, a chain of responsibility.
     */
    this._renderChain = new Chain ([
      new RenderInit (),
      new IdFilter (),
      new LinkFilter (),
      new NodeFilter (),
      new SourceDatabaseFilter (),
      new LegendFilter (),
      new CurvatureAdjuster ()
    ]);

    // Create rendering pipeline for schema
    this._schemaRenderChain = new Chain ([
      new RenderSchemaInit (),
      new RenderInit (),
      new IdFilter (),
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

    this._updateCacheViewer ();
  }
  /**
   * Updates the queries contained within the cache viewer modal.
   *
   */
  _updateCacheViewer () {
    const updateQueryTitle = (query, queryTitle) => {
      query.data.title = queryTitle;
      this._cache.db.cache.update(query.id,query);
      /* Gets a bit messy here but since it's directly modifying a property of the object, and these objects are all formatted and stored in the ref's state, we have to work around it a bit. */
      this.setState({ cachedQueries : this.state.cachedQueries });
      this._cachedQueriesModal.current.state.queries.forEach(q => {
        if (q.id === query.id) {
          q.title = query.data.title;
        }
      });
      this._cachedQueriesModal.current.setState({ queries : this._cachedQueriesModal.current.state.queries });
    }
    this._cache.db.cache.toArray().then((queries) => {
      queries = queries.map((query,i) => {
        let queryTitle;
        if (typeof query.data.title !== "undefined") {
          queryTitle = query.data.title;
        }
        else {
          queryTitle = "Query "+(i+1);
          updateQueryTitle(query,queryTitle);
        }
        // This is a function so that it is rerendered everytime the parent is rerendered, allowing it to update the `text` property.
        const editorTitle = () => (
            <InlineEdit validate={(text) => text.length > 0}
                        className="title-edit"
                        text={query.data.title}
                        paramName={'title'}
                        style={{}}
                        change={(data) => (updateQueryTitle(query,data.title))}></InlineEdit>
        );
        return {
          title: queryTitle,
          editorTitle: editorTitle,
          query:query.key,
          id: query.id
        };
      });
      this.setState({ cachedQueries : queries });
    });
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
    this.setState({},()=>this._findTool.current.updateResults());
  }
  /**
   * Highlight or unhighlight a given node or link type
   *
   * @param {String|String[]} - Type/Types which are highlighted or unhighlighted
   * @param {false|String|Number} highlight - Determines the new color.
   *    If false, it will be the original color.
   *    Otherwise, it must be a valid first argument for the Three.Color constructor.
   * @param {Boolean} [outline=true] - (NOT IMPLEMENTED) If true, the color will be an outline around the node. If false, it will directly modify the color of the node.
   *    NOTE: Only affects nodes.
   * @param {Object} [fade] - Determines the properties of the fading.
   * @param {Number} [fade.duration=250] - If duration is greater than 0, it will take `duration` number of seconds for the old color to fade into the new color.
   * @param {Number} [fade.offset=0] - Amount of time it takes before the fade begins.
   * @param {String} [property="type"] - Overrides `type` as the default property (e.g. `id` will highlight based on the `id` property).
   *
   * @private
   *
   * @returns {Promise} - (Only when using fade) Returns promise that resolves when the fade completes.
   */
  _highlightType (type, highlight, outline, fade, property) {
    if (typeof fade === "undefined") fade = {duration:250,offset:0};
    if (typeof property === "undefined") property = "type";
    if (!Array.isArray(type)) {
      type = [type];
    }

    if (typeof outline !== "boolean") {
      outline = true;
    }

    let highlightElements = [];

    // CLone all materials that have been reused by the react-force-graph so that we can modify individual elements
    let materialCache = [];

    let graph = this.state.schemaViewerActive && this.state.schemaViewerEnabled ? this.state.schema : this.state.graph;
    type.forEach(highlightType => {
      for (let graphElementType of ["nodes","links"]) {
        let elements = graph[graphElementType];
        for (let i=0;i<elements.length;i++) {
          let element = elements[i];
          let types = element[property];

          if (highlight !== false) {
            if (this.state.vMode !== "2D") {
              let obj = (element.__lineObj || element.__threeObj); //THREE.Mesh;
              if (obj === undefined) continue;
              let material = obj.material;
              if (materialCache.includes(material.uuid)) {
                obj.material = obj.material.clone();
                materialCache.push(obj.material.uuid);
              }
              else {
                materialCache.push(material.uuid);
              }
            }
          }

          if (!Array.isArray(types)) types = [types];
          if (types.includes(highlightType)) {
            highlightElements.push({
              graphElementType: graphElementType,
              element: element
            });
          }
        };
      }
    });
    return this.__highlightTypes(highlightElements, type, highlight, outline, fade);
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
          this._configureMessage (result[0].data)
          this._translateGraph (result[0].data)
          if (result[0].data.knowledge_graph.nodes.length + result[0].data.knowledge_graph.edges.length === 0) {
            this._handleMessageDialog (
              "Warning",
              "The query returned no results.",
              <div style={{whiteSpace:'pre-wrap'}}>Message object: <br/>{JSON.stringify(result[0].data,undefined,4)}</div>
            );
          }
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
                  this._handleMessageDialog (result.status, result.message, result.details);
                  console.log ("--error: " + result.message);
                  this.setState ({
                    loading : false,
                    error : result.message
                  });
                }
                // If there was no error or if it's just a warning continue on as if nothing happened.
                // Maybe remove caching on results with warnings?
                if (!result.message || result.status === "Warning") {
                  /* Convert the knowledge graph to a renderable form. */
                  if (result.answers) {
                    // answers is not kgs 0.9 compliant. ... longer story.
                    delete result.answers;
                  }
                  if ((result.knowledge_graph.nodes === undefined || result.knowledge_graph.edges === undefined) || (result.knowledge_graph.nodes.length + result.knowledge_graph.edges.length === 0)) {
                    this._handleMessageDialog (
                      "Warning",
                      "The query returned no results.",
                      <div style={{whiteSpace:'pre-wrap'}}>Message object: <br/>{JSON.stringify(result,undefined,4)}</div>
                    );
                  }
                  else {
                    this._configureMessage (result);
                    this._translateGraph (result);
                    this._cacheWrite (result);
                  }
                  this._setSchemaViewerActive(false);
                  this.setState({ loading : false });
                }
              },
              // Note: it's important to handle errors here
              // instead of a catch() block so that we don't swallow
              // exceptions from actual bugs in components.
              (error) => {
                this._handleMessageDialog (result.status, error.message, error.details);
                this.setState ({
                  loading : false,
                  error : error
                });
              }
            );
        }
      }.bind(this),
      function error (result) {
        this._handleMessageDialog (result.status, result.message, result.details);
        //console.log ("-- error", result);
      }.bind(this));
  }
  _cacheWrite (message) {
    //this._cache.write (this.state.code, result);
    // Clone message without bloat for storing inside the cache
    let {graph, hiddenTypes, ...cacheMessage} = message;
    var obj = {
      'key' : this.state.code,
      'data' : cacheMessage
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
                               record : result
                             });
                             localStorage.setItem ('code', obj.key);
                             this._updateCacheViewer ();
                           });
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
    if (message) {
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
      }, () => this._findTool.current.updateResults());
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
                   this._handleMessageDialog (result.status, result.message, result.details);
                   console.log ("--error: " + result.message);
                 }
                 if (result.answers) {
                   delete result.answers;
                 }

                 console.log("Fetched schema:", result);

                 this._schemaRenderChain.handle (result.schema, this.state);
                 result.schema.graph.links.forEach((link) => {
                   // Since opacity is based on weights and the schema lacks weighting, set it back to the default opacity.
                   delete link.linkOpacity;
                 });

                 this.setState({ schemaLoaded : true, schema : result.schema.graph, schemaMessage : result.schema });
                 this.state.schemaViewerActive && this._setSchemaViewerActive(true);

                 let { graph, hiddenTypes, ...schemaCachedMessage } = result.schema;

                 this._cache.write ('schema', {
                   'id' : 0,
                   'data' : schemaCachedMessage
                 });
               }
             );
           }
         }.bind(this),
         function error (result) {
           this._handleMessageDialog (result.status, result.message, result.details);
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
        this._highlightType(node.type, 0xff0000);
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
          this._highlightType(link.type, 0xff0000);
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
        this.state.selectMode)
    {
      // Select the node.
      this.setState ((prevState, props) => ({
        selectedNode : { link : link.origin }
      }));
      let width = this._graphSplitPane.current.splitPane.offsetWidth * (1/2);
      // For some reason react won't assign the underlying DOM element to the ref when using a callback ref.
      // Should replace this if possible as it is an escape hatch and not recommended for use, but the recommended alternative won't work.
      let toolbar = ReactDOM.findDOMNode(this._toolbar.current);
      if (toolbar.offsetHeight === this._graphSplitPane.current.splitPane.clientHeight) {
        // If the height of the toolbar has not been resized to be smaller, adjust the width so that it does not appear incorrect.
        // (If the toolbar covers that entire part of the graph, it looks incorrect and the object viewer appears larger)
        width += toolbar.offsetWidth / 2;
      }
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
    let graph = this.state.schemaViewerEnabled && this.state.schemaViewerActive ? this.state.schema : this.state.graph;
    // React-force-graph reuses material objects for multiple elements, so we need to clone every material so that we can modify individual elements.
    // ["nodes","links"].forEach((elementType) => {
    //   graph[elementType].forEach((element) => {
    //     if (this.state.visMode !== "2D") {
    //       let obj = (element.__lineObj || element.__threeObj);
    //       if (obj !== undefined) {
    //         obj._material = obj.material.clone();
    //         delete obj.material;
    //         // Sadly this is very hacky but it works. In order to prevent react-force-graph from reusing materials we have to clone the material everytime it tries to reassign it.
    //         obj.__defineGetter__("material", () => obj._material);
    //         obj.__defineSetter__("material", (material) => obj._material = material.clone());
    //       }
    //     }
    //   });
    // });
  }
  /**
   * Callback for when a legend button is right clicked
   *
   * @param {MouseEvent} e - The mouse event emited when the contextmenu event is fired (can be prevented),
   * @param {Boolean} active - If the button is active or not.
   * @param {String} type - The type that the button represents.
   *
   * @private
   */
  _legendButtonRightClick(e, active, type) {
    e.preventDefault();
    this._highlightType(type, 0xff0000, undefined, {duration:500, offset:0}).then(() => {
      this._highlightType(type, false, undefined, {duration:500, offset:2000});
    });
  }
  /**
   * Handle Legend callback on toggling of element type
   *
   * @param {string} graphElementType - Graph element type ("nodes" or "links")
   * @param {string|string[]} type - Type of element (e.g. "gene" or "affects_response_to")
   * @param {boolean} hidden - Determines the new visibility of the elements
   *
   * @private
   */
  _updateGraphElementVisibility(graphElementType, type, hidden) {
    let graph = this.state.schemaViewerEnabled && this.state.schemaViewerActive ? this.state.schema : this.state.graph;
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
               this.state.selectedNode.id !== node.id)
    {
      // Select the node.
      this.setState ((prevState, props) => ({
        selectedNode : { node: node.origin }
      }));
      let width = this._graphSplitPane.current.splitPane.offsetWidth * (1/2);
      // For some reason react won't assign the underlying DOM element to the ref when using a callback ref.
      // Should replace this if possible as it is an escape hatch and not recommended for use, but the recommended alternative won't work.
      let toolbar = ReactDOM.findDOMNode(this._toolbar.current);
      if (toolbar.offsetHeight === this._graphSplitPane.current.splitPane.clientHeight) {
        // If the height of the toolbar has not been resized to be smaller, adjust the width so that it does not appear incorrect.
        // (If the toolbar covers that entire part of the graph, it looks incorrect and the object viewer appears larger)
        width += toolbar.offsetWidth / 2;
      }
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
    // Should make this a single field such as `activeModal`
    this.setState({
      showSettingsModal: false,
      showTypeChart: false,
      showHelpModal: false,
    });
    this._exampleQueriesModal.current.hide();

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
   * Respond to changing the value of legend display limit
   * @param {string} type - Type of element (either "nodes" or "links").
   * @param {string} value - The new legend display limit (parsed as a base 10 integer)
   * @private
   */
  _onLegendDisplayLimitChange (type, event) {
    let value = parseInt(event.target.value);
    // parseInt returns NaN for anything that is not successfully parsed (e.g "foo" or "")
    if (isNaN(value)) {
      // Could possibly change this to be the max of said type (i.e. if there are 100 nodes value is set to 100)
      value = 0;
    }
    let prop = this.state.schemaViewerActive && this.state.schemaViewerEnabled ? "schemaLegendRenderAmount" : "queryLegendRenderAmount";
    // Either this.state.schemaLegendRenderAmount or this.state.queryLegendRenderAmount
    let renderAmountObj = this.state[prop];
    // Either ...legendRenderAmount.nodes or ...legendRenderAmount.links = value
    renderAmountObj[type] = value;
    value !== "" && this.setState({ prop : renderAmountObj });
    localStorage.setItem(prop, JSON.stringify(renderAmountObj));
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
            this._handleMessageDialog (result.status, result.message, result.details);
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
   * Invoked on window resize
   *
   * @private
   */
  _updateDimensions() {
    let node = this.state.selectedNode.node || this.state.selectedLink;
    let prevWinWidth = this._graphSplitPane.current.state.prevWinWidth;
    if (this.state.selectMode && node !== null && node.id !== undefined && node.id !== null &&
               this.state.selectedNode !== null &&
               this.state.selectedNode.id !== node.id)
    {
      let width = this._graphSplitPane.current.pane1.offsetWidth + (window.innerWidth - this._graphSplitPane.current.state.prevWinWidth);
      if (this.state.objectViewerEnabled) {
        // console.log(this._graphSplitPane.current.state.pane1Size);
        this._graphSplitPane.current.setState({ draggedSize : width, pane1Size : width , position : width });
      }
      this._updateGraphSize(width);
    }
    else {
      let width = this._graphSplitPane.current.splitPane.offsetWidth;
      if (this.state.objectViewerEnabled) {
        this._graphSplitPane.current.setState({ draggedSize : width, pane1Size : width , position : width });
      }
      this._updateGraphSize(width);
    }
    // For some reason react won't assign the underlying DOM element to the ref when using a callback ref.
    // Should replace this if possible as it is an escape hatch and not recommended for use, but the recommended alternative won't work.
    this._graphSplitPane.current.setState({prevWinWidth:window.innerWidth});
  }
  /**
   * Render the help modal
   *
   * @private
   */
  _renderHelpModal () {
    return (
      <Modal show={this.state.showHelpModal}
             onHide={() => this.setState({ showHelpModal : false })}
             dialogClassName="help-modal">
        <Modal.Header closeButton>
          <Modal.Title>
            Help and Information
          </Modal.Title>
        </Modal.Header>
        <Modal.Body style={{padding:"0"}}>
          <Container id="helpGrid">
            <Row>
              <Col>
                <Card>
                  <Card.Body>
                    <Card.Title>
                      Documentation
                    </Card.Title>
                    <Card.Text>
                      Documentation for TranQL
                    </Card.Text>
                    <Card.Link target="_blank" href="https://researchsoftwareinstitute.github.io/data-translator/apps/tranql">Go</Card.Link>
                  </Card.Body>
                </Card>
              </Col>
              <Col>
                <Card>
                  <Card.Body>
                    <Card.Title>
                      Examples
                    </Card.Title>
                    <Card.Text>
                      Some example queries to help get you started.
                    </Card.Text>
                    <Card.Link href="javascript:void(0)" onClick={() => {
                      this.setState({ showHelpModal : false });
                      this._exampleQueriesModal.current.show();
                    }}>View</Card.Link>
                  </Card.Body>
                </Card>
              </Col>
              <Col>
                <Card>
                  <Card.Body>
                    <Card.Title>
                      Toolbar Help
                    </Card.Title>
                    <Card.Text>
                      More in-depth explanations of Toolbar's functions and what they can be used for.
                    </Card.Text>
                    <Card.Link href="javascript:void(0)" onClick={() => {
                      this.setState({ showHelpModal : false, showToolbarHelpModal : true });
                    }}>View</Card.Link>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            <Row>
            </Row>
          </Container>
        </Modal.Body>
      </Modal>
    );
  }
  /**
   * Render the toolbar help modal
   *
   * @private
   */
   _renderToolbarHelpModal () {
     const obj = {
       buttons:this.state.buttons,
       tools:this.state.tools
     };
     return (
       <Modal show={this.state.showToolbarHelpModal}
              onHide={() => this.setState({ showToolbarHelpModal : false })}
              dialogClassName="toolbar-help-modal-dialog"
              className="toolbar-help-modal">
         <Modal.Header closeButton>
           <Modal.Title>
             Help and Information
           </Modal.Title>
         </Modal.Header>
         <Modal.Body>
           <Tabs className="toolbar-help-tabs">
              <TabList>
                {
                  Object.keys(obj).map((key, index) => {
                    return (
                      <Tab>{key.charAt(0).toUpperCase()+key.slice(1)}</Tab>
                    );
                  })
                }
              </TabList>
              {
                Object.entries(obj).map((entry, i) => {
                  let type = entry[0];
                  let values = entry[1];
                  return (
                    <TabPanel className="toolbar-help-tab-panel">
                      <ListGroup className="toolbar-help-tool-group">
                        {
                          values.map((val, n) => {
                            return (
                              <ListGroup.Item className="toolbar-help-tool-button" action active={n===this.state.toolbarHelpModalActiveToolType[type]} onClick={()=>{this.state.toolbarHelpModalActiveToolType[type] = n; this.setState({ toolbarHelpModalActiveToolType : this.state.toolbarHelpModalActiveToolType })}}>
                                {
                                  (() => {
                                    const noProps = (element) => {
                                      const newProps = {};
                                      Object.keys(element.props).forEach((k) => {
                                        // I don't know why this is necessary but it is.
                                        newProps[k] = undefined
                                      });
                                      return newProps;
                                    }
                                    const el = type === "tools" ? val.props.children : val;
                                    return React.cloneElement(el, noProps(el))
                                  })()
                                }
                              </ListGroup.Item>
                            );
                          })
                        }
                        <ListGroup.Item/>
                      </ListGroup>
                      <Card className="toolbar-help-content">
                        <Card.Body className="toolbar-help-content-body">
                          <Card.Header className="toolbar-help-content-title">
                          {this.state.toolHelpDescriptions[type][this.state.toolbarHelpModalActiveToolType[type]].title}
                          </Card.Header>
                          <Card.Text as="div">
                            <div>
                              {
                                this.state.toolHelpDescriptions[type][this.state.toolbarHelpModalActiveToolType[type]].description
                              }
                            </div>
                          </Card.Text>
                        </Card.Body>
                      </Card>
                    </TabPanel>
                  );
                })
              }
            </Tabs>
         </Modal.Body>
       </Modal>
     );
   }
  /**
   * Render the type bar chart modal
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
             dialogClassName="type-chart">
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
            </Form><br/>

            <b>Legend Display Limit</b><br/>
            <Form>
              <Form.Label>Set the number of nodes that the legend displays:</Form.Label>
              <Form.Control
              type="number"
              defaultValue={this.state.schemaViewerActive && this.state.schemaViewerEnabled ? this.state.schemaLegendRenderAmount.nodes : this.state.queryLegendRenderAmount.nodes}
              onChange={(e) => (this._onLegendDisplayLimitChange('nodes',e))}
              onKeyDown={(e) => {if (e.keyCode === 13) e.preventDefault();}}
              />
              <Form.Label>Set the number of links that the legend displays:</Form.Label>
              <Form.Control
              type="number"
              defaultValue={this.state.schemaViewerActive && this.state.schemaViewerEnabled ? this.state.schemaLegendRenderAmount.links : this.state.queryLegendRenderAmount.links}
              onChange={(e) => (this._onLegendDisplayLimitChange('links',e))}
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
   * Perform any necessary cleanup before being unmounted
   *
   * @private
   */
  componentWillUnmount() {
    window.removeEventListener('resize', this._updateDimensionsFunc);
    Object.values(this._highlightTypeFadeIntervals).forEach((interval)=>clearInterval(interval));
    Object.values(this._highlightTypeFadeTimeouts).forEach((timeout)=>clearTimeout(timeout));

  }
  /**
   * Handle events that can only occur once the component is mounted.
   *
   * @private
   */
  componentDidMount() {
    // this._updateDimensionsFunc = debounce(this._updateDimensions, 100);
    this._updateDimensionsFunc = this._updateDimensions;
    window.addEventListener('resize', this._updateDimensionsFunc);

    this._hydrateState ();

    // Populate concepts and relations metadata.
    this._getModelConcepts ();
    this._getModelRelations ();

    // Fetch schema
    this._getSchema ();

    this._updateGraphSize(document.body.offsetWidth);

    this.setState({}, () => {
      if (this.fg) {
        if (this.state.visMode === "2D") {
          // Loads too zoomed in. For some reason, if you set the first argument to `1`, it does nothing.
          this.fg.zoom(.99);
        }
      }
    });
  }

  render() {
    // Render it.
    return (
      <div className="App" id="AppElement">
        {this._renderModal () }
        {this._renderTypeChart ()}
        {this._renderHelpModal ()}
        {this._renderToolbarHelpModal ()}
        <QueriesModal ref={this._exampleQueriesModal}
                      runButtonCallback={(code, e) => {
                        this._exampleQueriesModal.current.hide();
                        this.setState({ code: code }, () => {
                          this._executeQuery();
                        });
                      }}
                      queries={this.state.exampleQueries}
                      title="Example queries"/>
        <QueriesModal ref={this._cachedQueriesModal}
                      id="cachedQueriesModal"
                      runButtonCallback={(code, e) => {
                        this._cachedQueriesModal.current.hide();
                        this.setState({ code: code }, () => {
                          this._executeQuery();
                        });
                      }}
                      queries={this.state.cachedQueries}
                      title="Cached queries"
                      tools={this.state.cachedQueriesModalTools}
                      emptyText=<div style={{fontSize:"17px"}}>You currently have no cached queries{!this.state.useCache && " (caching is disabled)"}.</div>/>
        <AnswerViewer show={true} ref={this._answerViewer} />
        <ReactTooltip place="left"/>
        <header className="App-header" >
          <div id="headerContainer" className="no-select">
            <p style={{display:"inline-block",flex:1}}>TranQL</p>
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
              <FaCog data-tip="Configure application settings" id="settings" className="App-control" onClick={this._handleShowModal} />
              <FaPlayCircle data-tip="Answer Navigator - see each answer, its graph structure, links, knowledge source and literature provenance" id="answerViewer" className="App-control" onClick={this._handleShowAnswerViewer} />
            </div>
          </div>
        </header>
        <div>
          {
            this.state.showCodeMirror ?
              (
                <>
                  <IoIosArrowDropupCircle onClick={(e) => this.setState({ showCodeMirror : false })} className="editor-vis-control legend-vis-control"/>
                  <CodeMirror ref={this._codemirror}
                  className="query-code"
                  value={this.state.code}
                  onBeforeChange={(editor, data, code) => this._updateCode(code)}
                  options={this.state.codeMirrorOptions}
                  autoFocus={true} />
                </>
              ) :
              (
                <div className="editor Legend" data-closed={true}>
                <IoIosArrowDropdownCircle className="editor-vis-control legend-vis-control-open"
                onClick={(e) => this.setState({ showCodeMirror : true })}
                color="rgba(40,40,40,1)"
                />
                </div>
              )
          }
          <Legend typeMappings={this.state.graph.typeMappings}
                  hiddenTypes={this.state.graph.hiddenTypes}
                  nodeTypeRenderAmount={this.state.queryLegendRenderAmount.nodes}
                  linkTypeRenderAmount={this.state.queryLegendRenderAmount.links}
                  callback={this._updateGraphElementVisibility}
                  onContextMenu={this._legendButtonRightClick}
                  render={(!this.state.schemaViewerActive || !this.state.schemaViewerEnabled) && this.state.colorGraph}/>
          <Legend typeMappings={this.state.schema.typeMappings}
                  hiddenTypes={this.state.schema.hiddenTypes}
                  nodeTypeRenderAmount={this.state.schemaLegendRenderAmount.nodes}
                  linkTypeRenderAmount={this.state.schemaLegendRenderAmount.links}
                  callback={this._updateGraphElementVisibility}
                  onContextMenu={this._legendButtonRightClick}
                  render={this.state.schemaViewerActive && this.state.schemaViewerEnabled && this.state.colorGraph}/>
          <div id="graph"></div>
          <div id="viewContainer">
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
                  <div id="bottomContainer">
                    {
                      this.state.toolbarEnabled && (
                        <Toolbar id="toolbar"
                                 default={0}
                                 tools={this.state.tools}
                                 buttons={this.state.buttons}
                                 onlyUseShortcutsWhen={[HTMLBodyElement]}
                                 ref={this._toolbar}/>
                      )
                    }
                    <div id="graphOverlayContainer">
                      <div id="schemaBanner" className="no-select" style={{display:(this.state.schemaViewerEnabled ? "" : "none")}}>
                        {((this.state.schemaViewerActive && !this.state.schemaLoaded) || (!this.state.schemaViewerActive && this.state.loading)) && <FaSpinner style={{marginRight:"10px"}} className="fa-spin"/>}
                        {this.state.schemaViewerActive ? "Schema:" : "Graph:"}
                        <div id="schemaViewToggleButtonContainer">
                          <Button color="primary"
                                  id="schemaViewToggleButton"
                                  size="sm"
                                  onClick={(e) => this._setSchemaViewerActive (!this.state.schemaViewerActive)}
                          >
                          {this.state.schemaViewerActive ? "Show graph" : "Show schema"}
                          </Button>
                        </div>
                      </div>
                      <LinkExaminer link={this.state.selectedNode}
                                    render={this.state.connectionExaminer && this.state.selectedNode !== null && this.state.selectedNode.hasOwnProperty('link')}/>
                      <FindTool graph={this.state.schemaViewerActive && this.state.schemaViewerEnabled ? this.state.schema : this.state.graph}
                                resultMouseEnter={(values)=>{
                                  console.log(values);
                                  values.forEach((element) => this._highlightType(element.source_el.id,0xff0000,false,undefined,'id'))}
                                }
                                resultMouseLeave={(values)=>{
                                  values.forEach((element) => this._highlightType(element.source_el.id,false,false,undefined,'id'))}
                                }
                                resultMouseClick={(values)=>{}}
                                ref={this._findTool}/>
                    </div>
                  </div>
                  <div onContextMenu={this._handleContextMenu}>
                    {this.state.schemaViewerActive && this.state.schemaViewerEnabled ?
                      (
                        this._renderForceGraph (
                          this.state.schema,
                          {
                          ref: (el) => {if (this.state.schemaViewerActive) this.fg = el; this._updateFg ()}
                        })
                      )
                    :
                      (
                        this._renderForceGraph (
                          this.state.graph, {
                          ref: (el) => {if (!this.state.schemaViewerActive) this.fg = el; this._updateFg ()}
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
