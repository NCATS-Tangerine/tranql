import React, { Component } from 'react';
import { Modal, ListGroup, Container, Row } from 'react-bootstrap';
import { Controlled as CodeMirror } from 'react-codemirror2';
import { FaPlay, FaUndo } from 'react-icons/fa';
import ReactTooltip from 'react-tooltip';
import './ExampleQueriesModal.css';

/**
 * Modal component for display example querying and allowing for easy editing and execution of them.
 */
export default class ExampleQueriesModal extends Component {
  /**
   * Constructs the component
   *
   * @param {Object} props - The properties of the model
   * @param {Object[]} props.examples - Array of examples with structure {`title`: string, `query`: string}
   * @param {function} props.setActiveCallback - Invoked when the run button is pressed. Passed the arguments code<String> and event<MouseEvent>
   *
   */
  constructor(props) {
    super(props);

    /**
     *
     *
     */
    this.state = {
      show: false,
      currentExampleIndex: 0,
      examples: this.props.examples
    };
    this.state.examples.forEach((ex) => ex.editedQuery = ex.query);
    this.show = this.show.bind (this);
    this.hide = this.hide.bind (this);

    this._modalBody = React.createRef();
  }
  /**
   * Show the modal
   */
  show() {
    this.setState({ show : true });
  }
  /**
   * Hide the modal
   */
  hide() {
    this.setState({ show : false });
  }
  /**
   * Getter method which returns the currently active example query
   */
  get currentExample() {
    return this.state.examples[this.state.currentExampleIndex];
  }
  // May set the current example by either title or index
  /**
   * Setter method to set the currently active example query.
   *
   * @param {String|Number} value - If of type String, it sets the example based on title. If of type Number, it sets the example based on index.
   */
  set currentExample(value) {
    if (typeof value === "string") {
      for (let i=0;i<this.state.examples.length;i++) {
        let example = this.state.examples[i];
        if (example.title === value) {
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
        <Modal.Body ref={this._modalBody}>
          <ReactTooltip place="right"/>
          <Container fluid={true} className="container">
            <Row style={{flexWrap:"nowrap"}}>
              <ListGroup className="example-list">
                {
                  this.state.examples.map((example, i) => {
                    return (
                      // On click, set the current example and scroll back to the top
                      <ListGroup.Item active={this.state.currentExampleIndex===i} action onClick={() => {this.currentExample = i;this._modalBody.current.scrollTop = 0;}}>
                        {example.title}
                      </ListGroup.Item>
                    );
                  })
                }
                {/* This empty item is in order to add a border to the entire list group */}
                {/*<ListGroup.Item />*/}
              </ListGroup>
              <div className="right-container">
                <div className="example-query-button-container">
                  <FaPlay data-tip="Run the query" onClick={(e) => this.props.setActiveCallback(this.currentExample.editedQuery, e)}/>
                  <FaUndo data-tip="Reset the example" onClick={() => {
                    this.currentExample.editedQuery = this.currentExample.query;
                    this.setState({ examples : this.state.examples });
                  }}/>
                </div>
                <CodeMirror className="example-query-code"
                            value={this.currentExample.editedQuery}
                            onBeforeChange={(editor,data,code) => {
                              this.currentExample.editedQuery = code;
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
