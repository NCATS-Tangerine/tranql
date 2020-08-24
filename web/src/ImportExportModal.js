import React, { Component } from 'react';
import { Modal, Container, Row, Form, Button, InputGroup } from 'react-bootstrap';
import { FaFileImport, FaFileExport } from 'react-icons/fa';
import { NotificationManager } from 'react-notifications';
import FileSaver from 'file-saver';
import * as qs from 'qs';
import * as YAML from 'js-yaml';
import FileLoader from './FileLoader.js';
import GraphSerializer from './GraphSerializer.js';

export default class ImportExportModal extends Component {
  constructor(props) {
    super(props);

    this.state = {
      importForm : {
        cacheGraph : false
      },
      exportForm : {
        saveGraphState : true,
        readable : false,
        fileFormat: 'JSON'
      },
    };

    this._importForm = React.createRef ();
    this._exportForm = React.createRef ();
  }
  /**
   * Dumps the graph to a given serialization format
   *
   * @param {Object} graph - The graph object to dump
   * @param {String} exportType - A string of type "JSON" or "YAML"
   * @param {Boolean} readable - A boolean indicating whether the graph should be dumped in a readable form or a minimally-sized form
   *
   * @returns {Object} - An object containing the dumped graph and file extension
   * @private
   */
  _dumpGraph(graph,exportType,readable) {
    let extension;
    if (exportType === 'JSON') {
      let indent = readable ? 2 : 0;
      graph = JSON.stringify(graph,undefined,indent);
      extension = '.json';
    }
    else if (exportType === 'YAML') {
      let options = readable ? {} : {indent:0,noRefs:true,condenseFlow:true,noArrayIndent:true};
      graph = YAML.safeDump(graph,options);
      extension = '.yaml';
    }
    return { graph, extension };
  }
  /**
   * Returns the formatted graph for exportation
   *
   * @param {Boolean} saveGraphState - Specifies whether or not the graph will save its current state
   *
   * @returns {Object} - The exportable graph
   * @private
   */
  _getExportGraph(saveGraphState) {
    let graph = this.props.record;
    if (saveGraphState) {
      graph.data.graph = GraphSerializer.serialize(this.props.graph);
    }
    return graph;
  }
  render() {
    return (
      <Modal show={this.props.activeModal==="ImportExportModal"}
             onHide={() => this.props.setActiveModal(null)}
             dialogClassName="import-export-modal-dialog"
             className="import-export-modal">
        <Modal.Header closeButton>
          <Modal.Title>
            Import/Export Graph
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Container>
            <Row>
                <div className="no-select">
                  <div className="import-export-icon-container horizontal-bar">
                    <FaFileImport/>
                    <span>Import a graph</span>
                  </div>
                    <div className="import-options-container">
                      {<Form noValidate onSubmit={(e)=>{e.preventDefault();}} ref={this._importForm}>
                        <Form.Check inline label="Cache the graph" name="importCacheGraph" checked={this.state.importForm.cacheGraph} onChange={(e)=>{
                          const importForm = this.state.importForm;
                          importForm.cacheGraph = e.target.checked;
                          this.setState({ importForm });
                        }}/>
                        <FileLoader pondProps={{allowMultiple:false,maxFiles:1,acceptedFileTypes:['.json','.yaml','.yml']}}
                                    buttonProps={{type:"submit"}}
                                    filesLoadedCallback={(graph) => {
                                      graph = graph[0];
                                      if (!graph) return;

                                      const options = this.state.importForm;
                                      this.props.importGraph(graph, options);
                                    }}
                                    loadFile={(mimeType,data) => {
                                      let message;
                                      try {
                                        if (mimeType === "application/json") {
                                          message = JSON.parse(data);
                                        }
                                        else if (mimeType === "text/yaml") {
                                          message = YAML.safeLoad(data);
                                        }
                                      }
                                      catch (error) {
                                        this._handleMessageDialog("Graph Parsing Error", error.message, error.stack);
                                      }
                                      return message;
                                    }}/>
                      </Form>}
                    </div>
                </div>
                <div className="no-select">
                  <div className="import-export-icon-container horizontal-bar">
                    <FaFileExport/>
                    <span>Export graph{(() => {
                      // if (this.state.record) {
                        // Was lagging it so it has been removed for now
                        // const options = this.state.exportForm;
                        // const obj = this._getExportGraph(options.saveGraphState);
                        // Assumes ANSI encoding
                        // return " (" + formatBytes(this._dumpGraph(obj,options.fileFormat).graph.length,1) + ")";
                      // }
                    })()}</span>
                  </div>
                    <div className="export-options-container">
                      <Form noValidate onSubmit={(e)=>{e.preventDefault();}} ref={this._exportForm}>
                        <Form.Check inline label="Save graph state" name="exportSaveState" checked={this.state.exportForm.saveGraphState} onChange={(e)=>{
                          const exportForm = this.state.exportForm;
                          exportForm.saveGraphState = e.target.checked;
                          this.setState({ exportForm });
                        }}/>
                        <Form.Check inline label="Export in readable form" name="exportReadable" checked={this.state.exportForm.readable} onChange={(e)=>{
                          const exportForm = this.state.exportForm;
                          exportForm.readable = e.target.checked;
                          this.setState({ exportForm });
                        }}/>
                        <Form.Group className="form-inline">
                          <Form.Label>File format:</Form.Label>
                          <Form.Control as="select" name="exportFileFormat" value={this.state.exportForm.fileFormat} onChange={(e)=>{
                            const exportForm = this.state.exportForm;
                            exportForm.fileFormat = e.target.value;
                            this.setState({ exportForm });
                          }}>
                            <option>JSON</option>
                            <option>YAML</option>
                          </Form.Control>
                        </Form.Group>
                        <div style={{width:"100%",flexGrow:1,display:"flex",justifyContent:"center",alignItems:"flex-end"}}>
                          <Button color="primary"
                                  style={{width:"100%"}}
                                  onClick={() => {
                                    // Prevent exportation of graph if one has not been loaded
                                    // Also prevents exportation of schema (would be fairly simple to add but for now is not very useful)
                                    if (!this.props.record) {
                                      NotificationManager.warning('You must load a graph', 'Warning', 4000);
                                      return;
                                    }
                                    const options = this.state.exportForm;
                                    const exportType = options.fileFormat;
                                    const readable = options.readable;
                                    const graph = this._getExportGraph(options.saveGraphState);

                                    const {graph: data, extension} = this._dumpGraph(graph,exportType,readable);

                                    data && FileSaver.saveAs(new Blob([data]),'graph'+extension);
                                  }}
                                  {...(!this.props.record ? {className: 'disabled'} : {})}>
                            Confirm
                          </Button>
                        </div>
                      </Form>
                    </div>
                </div>
            </Row>
            <Row>
              <div className="copy-url-container">
                <InputGroup>
                  <InputGroup.Prepend><InputGroup.Text>Share this query:</InputGroup.Text></InputGroup.Prepend>
                  <Form.Control type="text" onFocus={(e) => {
                    e.target.select();
                  }} value={(() => {
                    let url = window.location.href.split("?")[0];
                    return url + "?" + qs.stringify({ q : this.props.code });
                  })()} readOnly/>
                  {/*<InputGroup.Append><InputGroup.Text><FaCopy/></InputGroup.Text></InputGroup.Append>*/}
                </InputGroup>
              </div>
            </Row>
          </Container>
        </Modal.Body>
      </Modal>
    );
  }
}
