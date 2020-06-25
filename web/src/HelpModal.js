import React, { Component } from 'react';
import { Modal, Container, Row, Col, Card, Tabs, Tab, ListGroup } from 'react-bootstrap';
import { FaMousePointer } from 'react-icons/fa';
import { scrollIntoView } from './Util.js';

export default class HelpModal extends Component {
  render() {
    return (
      <Modal show={this.props.activeModal==="HelpModal"}
             onHide={() => this.props.setActiveModal(null)}
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
                    <Card.Link target="_blank" rel="noopener noreferrer" href="https://researchsoftwareinstitute.github.io/data-translator/apps/tranql">Go</Card.Link>
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
                    {/*eslint-disable-next-line*/}
                    <Card.Link href="javascript:void(0)" onClick={() => {
                      this.props.setActiveModal('ExampleQueriesModal');
                    }}>View</Card.Link>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            <Row>
              <Col>
                <Card>
                  <Card.Body>
                    <Card.Title>
                      Toolbar Help
                    </Card.Title>
                    <Card.Text>
                      More in-depth explanations of Toolbar's functions and what they can be used for.
                    </Card.Text>
                    {/*eslint-disable-next-line*/}
                    <Card.Link href="javascript:void(0)" onClick={() => {
                      this.props.setActiveModal('ToolbarHelpModal');
                    }}>View</Card.Link>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Container>
        </Modal.Body>
      </Modal>
    );
  }
}

export class ToolbarHelpModal extends Component {
  constructor(props) {
    super(props);

    this.state = {
      toolbarHelpModalActiveToolType : {
        buttons: 0,
        tools: 0
      }
    };

    this.toolHelpDescriptions = {
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
          From there, you can navigate the tree view of the selected object and view all the properties that it has. The object viewer is inside a horizontal split pane
          along with the graph, so it may be resized by dragging the border where the two intersect.`
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
          Clicking on a link will bring it up in the object viewer.
          `
        },
        {
          title: "Browse Node",
          description: `
          This tool allows you to select a node and browse connections it has with nodes of a given type, optionally along a given prediate. It will
          query the Robokop API and return new nodes.
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
              <Tabs className="find-tool-tabs" defaultActiveKey="overview">
                <Tab eventKey="overview" title="Overview">
                  <p>
                    This button brings up the find tool, which can also be opened with the keyboard shortcut control+F (the normal browser find tool can be opened with F3).
                    The find tool enables you to use JSONPath or JSON-like attribute selectors to find objects in the graph. Additionally, you may use tools on the results.
                    <br/><br/>
                    The JSONPath syntax is limited relative to the normal syntax in that you cannot select node pairs ({`nodes->links->nodes`}).
                    However, JSONPath also allows for the exploration of the entire graph object, rather than only selecting nodes and links.
                    Another advantage of the JSONPath syntax is that you do not need to know JSONPath to use it, as you can explore the graph via the arrows
                    on the results.
                  </p>
                </Tab>
                <Tab eventKey="normalSyntax" title="Normal Syntax">
                  <div className="section">
                    <h6>Structure:</h6>
                    <p>
                      The general structure of queries is `selector`{"{`attributes`}"}. A selector can be either "nodes", "links", or "*". The asterisk selector selects both nodes and links.
                      You can also connect these selectors with transitions, with the structure `selector`{"{`attributes`}"} -> `selector`{"{`attributes`}"} -> `selector`{"{`attributes`}"}. Note: only links are applicable in the second selector.
                      The `{"{}"}` following the selector may be omitted if no attributes are present.
                      Attributes must be valid <a target="_blank" rel="noopener noreferrer" href="https://tools.ietf.org/html/rfc7159">JSON</a>. This means that attributes are structured as key to value, where key is an attribute that a node or link may or may not possess.
                      If you are unsure as to what attributes nodes and links have, you can use the <FaMousePointer style={{fontSize:"14px"}}/> select tool to view a node or link's attributes.
                      However, keep in mind, only some attributes such as "id", "name", "type", and "equivalent_identifiers" are standard. Not all nodes or links are gaurenteeed to have others.
                    </p>
                    <div className="section">
                      <h6>Flags:</h6>
                      <p>
                        A colon in an attribute key indicates that the following text is an attribute flag.
                        Attribute flags modify the behavior of how the attribute is compared to the provided value.
                        For example, if an attribute is a list (['a','b','c']), you can use the `includes` (pseudo) flag to check if `a` is in the list.
                        This would look like "nodes{`{"attribute:includes" : "a"}`}".
                        All normal colons inside of attribute keys must be escaped, i.e. preceded by a backslash ("\:"),
                        or it will be assumed that the following text is an attribute flag. A scenario in which it would be necessary to do this would be
                        nodes{`{"a:test":'value'}`} where you wanted to select nodes whose attribute "a:test" has the value "value".
                        Only one attribute flag can currently be used in an attribute.<br/>
                        <span style={{fontWeight:600}}>Example:</span> nodes{`{"omnicorp_article_count:>=":100}`} selects all nodes whose `omnicorp_article_count`
                        attribute is greater than or equal to 100. The flag in this query is ">=".
                      </p>
                      <div className="section">
                        <h6>The valid flags are:</h6>
                        <Row>
                          <dl>
                            {/*eslint-disable-next-line*/}
                            <Col><dt>regex</dt></Col><Col><dd>Matches a <a target="_blank" rel="noopener noreferrer" href="http://cecas.clemson.edu/~warner/M865/RegexBasics.html">regular expression</a> against the element's attribute<br/><a href="javascript:void(0)" onClick={
                              ()=>scrollIntoView("#regexFlag")
                            }>Example</a></dd></Col>
                            {/*eslint-disable-next-line*/}
                            <Col><dt>func</dt></Col><Col><dd>Evals a JavaScript function which is passed the element's attribute as the only argument. Should return true or false to indicate if the node should or should not be included.<br/><a href="javascript:void(0)" onClick={
                              ()=>scrollIntoView("#funcFlag")
                            }>Example</a></dd></Col>
                            <Col><dt>Comparison Operators</dt></Col><Col><dd>The comparison operators <b>({"<"}, {"<="}, {">"}, {">="}, {"=="}, {"==="}, {"!="}, {"!=="})</b> are all valid flags. {"<="} and {">="} compare if a number is less than or equal to and greater than or equal to the given input respectively.
                            "!=" and "!==" both compare if it is not equal to the given input. The "===" and "!==" operators do not allow for implicit conversion when comparing, and therefore should almost always be used over their alternative.</dd></Col>
                            <Col>
                              <dt>Pseudo Flags</dt>
                              <dd>
                                Any other method or property in the element's attribute's JavaScript prototype chain (for common references see&nbsp;
                                <a target="_blank" rel="noopener noreferrer" href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/prototype">Text</a> and&nbsp;
                                <a target="_blank" rel="noopener noreferrer" href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/prototype">Lists</a>).
                                {/*eslint-disable-next-line*/}
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

                            <Col><dt>__nodes__</dt></Col><Col><dd>The value of __nodes__ is a list of the all the nodes in the current force graph</dd></Col>

                            <Col><dt>__links__</dt></Col><Col><dd>The value of __links__ is a list of the all the links in the current force graph</dd></Col>
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
                        <Col><dd>This will find all nodes in the graph (schema) whose `id` attribute equals "chemical_substance".</dd></Col>

                        <Col id="regexFlag"><dt>nodes{`{"equivalent_identifiers:includes":"CHEMBL:CHEMBL3"}`} -><br/> links{`{"type:includes":"related_to"}`} -><br/> nodes{`{"name:regex":"(disease|genetic_condition)"}`}</dt></Col>
                        <Col><dd>This will find all nodes in the graph who have the curie "CHEMBL:CHEMBL3" in their equivalent_identifiers attribute, all nodes whose name matches the regular expression "(disease|genetic_condition)",
                        and all links whose source is any node from the first selector, target is from the third selector, and has the type "related_to".</dd></Col>

                        <Col id="funcFlag"><dt>nodes{`{"description:func":"function(description) { return description.split("/").includes('test'); }"}`}</dt></Col>
                        <Col><dd>This will find all nodes in the graph whose `description` attribute split by a forward slash contains the string "test".</dd></Col>
                      </dl>
                    </Row>
                  </div>
                </Tab>
                <Tab eventKey="JSONPath" title="JSONPath">
                  <div className="section">
                    <h6>Structure:</h6>
                    <p>
                      When using JSONPath, the root is the graph object. Every JSONPath result that can be explored
                      has forward arrows which will set your query to be the result's results. If the results are node or link objects
                      ($.nodes.{"{}"} or $.links.{"{}"} or $.*.{"{}"}), you can use tools on them like the normal syntax.<br/><br/>
                      <span style={{fontWeight:"600"}}>If using filters, please note that the object viewer displays the element's `origin` attribute.
                      The origin attribute contains almost all relevant information.</span><br/><br/>
                      For an extensive JSONPath reference, see <a target="_blank" rel="noopener noreferrer" href="https://goessner.net/articles/JsonPath/">this</a>.<br/>
                      For the specific JSONPath module in use, see <a target="_blank" rel="noopener noreferrer" href="https://www.npmjs.com/package/jsonpath">this</a>.
                    </p>
                  </div>
                  <div className="section">
                    <h6>Example queries:</h6>
                    <Row>
                      <dl>
                        <Col><dt>$.nodes[?(@.origin.id === 'chemical_substance')]</dt></Col>
                        <Col><dd>This will find all nodes in the graph (schema) whose origin's `id` attribute equals "chemical_substance".</dd></Col>

                        <Col><dt>$.nodes[?(@.origin.equivalent_identifiers.includes("CHEMBL:CHEMBL3"))]</dt></Col>
                        <Col><dd>This will find all nodes in the graph who have the curie "CHEMBL:CHEMBL3" in their origin's "equivalent_identifiers" attribute.</dd></Col>

                        <Col><dt>$.*[?(@.origin.reasoner.includes('rtx'))]</dt></Col>
                        <Col><dd>This will find all nodes and links in the graph whose `reasoner` attribute includes "rtx"</dd></Col>

                        <Col><dt>$.links[?(@.origin.source_database.includes('mychem') && @.target.origin.omnicorp_article_count >= 1000)]</dt></Col>
                        <Col><dd>This will find all links in the graph whose whose origin's source database includes "mychem"
                        and whose target node's origin has an `omnicorp_article_count` greater than or equal to 1000</dd></Col>
                      </dl>
                    </Row>
                  </div>
                </Tab>
              </Tabs>
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
          title: "Import/Export",
          description: `
          This button brings up the import/export interface which allows you to import and export TranQL force graphs
          into various file formats that can then be loaded by others. The graphs retain their visual state upon exportation.`
        },
        {
          title: "Settings",
          description: (
            <Tabs defaultActiveKey="overview">
              <Tab eventKey="overview" title="Overview">
                This button brings up the settings interface, which allows you to customize the behavior of TranQL.
              </Tab>
              <Tab eventKey="general" title="General">
                <h6>Visualization Mode and Graph Colorization</h6>
                  <p>This allows you to change the way that the graph is visualized. You may also disable the coloring of the graph if desired.</p>
                <h6>Use Cache</h6>
                  <p>This allows you to disable the caching of the TranQL schema and any results from TranQL queries. This means that the results will not be stored locally
                  on your machine for future use. Disabling the cache will not delete your currently cached queries.
                  You may also clear the cache if desired.</p>
                <h6>Cursor</h6>
                  <p>This sets your mouse cursor to be the same icon as the currently selected tool.</p>
              </Tab>
              <Tab eventKey="graphStructure" title="Graph Structure">
                <h6>Link Weight Range</h6>
                  <p>This will filter out any links from the graph whose weights are not within the specified range.</p>
                <h6>Node Connectivity Range</h6>
                  <p>This will filter out any nodes from the graph whose number of connections (links) with other nodes is not within the specified range.</p>
                <h6>Force Graph Charge</h6>
                  <p>This will set the charge force applied to nodes within the graph. Charge is a property that acts like an electrical charge and causes either
                  the attraction or repulsion of nodes between one another. It can be used to get a more enlarged and spread out view of the graph and prevent
                  nodes from overlapping. <a target="_blank" rel="noopener noreferrer" href="https://d3-wiki.readthedocs.io/zh_CN/master/Force-Layout/#charge">More comprehensive reference</a></p>
                <h6>Legend Display Limit</h6>
                  <p>This will filter out any node or link types in the legend following the given value. Nodes and links in the legend are ordered
                  by greatest to least quantity within the graph, thus, it results in the least-present types being filtered out of the legend.</p>
              </Tab>
              <Tab eventKey="knowledgeSources" title="Knowledge Sources">
                <h6>Database Sources</h6>
                  <p>When a query is active, this setting will be populated with checkboxes for all source databases that the query was constructed from.
                  You can then disable sources to filter them out of the graph.</p>
                <h6>Reasoner Sources</h6>
                  <p>When a query is active, this setting will be populated with checkboxes for all source reasoners that the query was constructed from.
                  You can then disable sources to filter them out of the graph.</p>
              </Tab>
            </Tabs>
          )
        },
        {
          title: "Table View",
          description: `
          This button brings up a tabular representation of the active graph. The table viewer is in a vertical split pane along with the graph,
          so it may be resized by dragging the border where the two intersect to take up more or less space if desired.
          Regex may also be used in the filters by entering a regex literal (e.g. /^.*$/).
          For example, if you wanted to find all elements whose reasoner property includes RTX, you could use the pattern "/^- rtx$/m".
          `
        },
        {
          title: "Interactive Shell",
          description: (<p>
          This button brings up an interactive Python shell/script editor. The shell is in the same split pane as the table viewer, and the two
          cannot be used simultaneously. Within the shell, the \`tranql\` global is defined with various utilities.
          <br/><br/>
          Note: tranql.install_module(module) must be called prior to usage in a script or it will not be usable. Additionally, tranql.install_module
          does not automatically import the module.
          </p>)
        }
      ]
    };
  }
  render() {
    const obj = {
      buttons:React.Children.toArray(this.props.buttons.props.children),
      tools:React.Children.toArray(this.props.tools.props.children)
    };
    return (
      <Modal show={this.props.activeModal==="ToolbarHelpModal"}
             onHide={() => this.props.setActiveModal(null)}
             dialogClassName="toolbar-help-modal-dialog"
             className="toolbar-help-modal">
        <Modal.Header closeButton>
          <Modal.Title>
            Help and Information
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Tabs defaultActiveKey="0" className="toolbar-help-tabs">
             {
               Object.entries(obj).map((entry, i) => {
                 let type = entry[0];
                 let values = entry[1];

                 const title = type.charAt(0).toUpperCase()+type.slice(1)
                 return (
                   <Tab eventKey={i.toString()} className="toolbar-help-tab-panel" key={i} title={title}>
                     <ListGroup className="toolbar-help-tool-group">
                       {
                         values.map((val, n) => {
                           return (
                             // eslint-disable-next-line
                             <ListGroup.Item className="toolbar-help-tool-button" key={n} action active={n===this.state.toolbarHelpModalActiveToolType[type]} onClick={()=>{
                               this.state.toolbarHelpModalActiveToolType[type] = n;
                               this.setState({ toolbarHelpModalActiveToolType : this.state.toolbarHelpModalActiveToolType })
                             }}>
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
                         {this.toolHelpDescriptions[type][this.state.toolbarHelpModalActiveToolType[type]].title}
                         </Card.Header>
                         <Card.Text as="div">
                           <div>
                             {
                               this.toolHelpDescriptions[type][this.state.toolbarHelpModalActiveToolType[type]].description
                             }
                           </div>
                         </Card.Text>
                       </Card.Body>
                     </Card>
                   </Tab>
                 );
               })
             }
           </Tabs>
        </Modal.Body>
      </Modal>
    );
  }
}
