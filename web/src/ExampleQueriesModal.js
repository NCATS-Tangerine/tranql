import React, { Component } from 'react';
import { Modal, ListGroup, Container, Row } from 'react-bootstrap';
import { Controlled as CodeMirror } from 'react-codemirror2';
import { FaPlay, FaUndo } from 'react-icons/fa';
import ReactTooltip from 'react-tooltip';
import './ExampleQueriesModal.css';

export default class ExampleQueriesModal extends Component {
  constructor(props) {
    super(props);

    this.state = {
      show: false,
      currentExampleIndex: 0,
      examples: [
        {
          name: 'foo',
          body: 'testing foo'
        },
        {
          name: 'bar',
          body: 'testing bar'
        }
      ]
    };
    this.state.examples.forEach((ex) => ex.editedBody = ex.body);
    this.show = this.show.bind (this);
    this.hide = this.hide.bind (this);

    this.currentExample = 0;
  }
  show() {
    this.setState({ show : true });
  }
  hide() {
    this.setState({ show : false });
  }
  get currentExample() {
    return this.state.examples[this.state.currentExampleIndex];
  }
  // May set the current example by either name or index
  set currentExample(value) {
    if (typeof value === "string") {
      for (let i=0;i<this.state.examples.length;i++) {
        let example = this.state.examples[i];
        if (example.name === value) {
          value = i;
          break;
        }
      }
    }
    this.setState({ currentExampleIndex : value });
  }
  render() {
    return (
      <Modal show={this.state.show}
             onHide={this.hide}
             dialogClassName="example-queries-modal-dialog"
             className="example-queries-modal">
        <Modal.Header closeButton>
          <Modal.Title>
            Example Queries
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <ReactTooltip place="right"/>
          <Container fluid={true} className="container">
            <Row style={{height:"100%",maxHeight:"100%",flexWrap:"nowrap"}}>
              <ListGroup className="example-list">
                {
                  this.state.examples.map((example, i) => {
                    return (
                      <ListGroup.Item active={this.state.currentExampleIndex===i} action onClick={() => this.currentExample = i}>
                        {example.name}
                      </ListGroup.Item>
                    );
                  })
                }
                {/* This empty item is in order to add a border to the entire list group */}
                <ListGroup.Item />
              </ListGroup>
              <div className="right-container">
                <div className="example-query-button-container">
                  <FaPlay data-tip="Run the query" onClick={(e) => this.props.setActiveCallback(this.currentExample.editedBody, e)}/>
                  <FaUndo data-tip="Reset the example" onClick={() => {
                    this.currentExample.editedBody = this.currentExample.body;
                    this.setState({ examples : this.state.examples });
                  }}/>
                </div>
                <CodeMirror className="example-query-code"
                            value={this.currentExample.editedBody}
                            onBeforeChange={(editor,data,code) => {
                              this.currentExample.editedBody = code;
                              this.setState({ examples : this.state.examples });
                            }}
                            options={{
                              lineNumbers: true,
                              mode: 'text/x-pgsql', //'text/x-pgsql',
                              tabSize: 2,
                              readOnly: false,
                              lineWrapping: true
                            }}/>
              </div>
            </Row>
          </Container>
        </Modal.Body>
      </Modal>
    );
  }
}
