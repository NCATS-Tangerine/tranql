import React, { Component } from 'react';
import { Modal, ListGroup, Container, Row } from 'react-bootstrap';
import { Controlled as CodeMirror } from 'react-codemirror2';
import { FaPlay, FaUndo } from 'react-icons/fa';
import ReactTooltip from 'react-tooltip';
import './QueriesModal.css';

/**
 * Modal component for displaying a list of queries and allowing for easy editing and execution of them.
 */
export default class QueriesModal extends Component {
  /**
   * Constructs the component
   *
   * @param {Object} props - The properties of the model
   * @param {Object[]} props.queries - Array of queries with structure {`title`: string, `query`: string}. Will initially set the queries after mount.
   *    NOTE: The modal will error and not function if props.queries is left empty
   * @param {function} props.setActiveCallback - Invoked when the run button is pressed. Passed the arguments code<String> and event<MouseEvent>
   * @param {String} props.title - Title of the modal.
   * @param {String|React.Component} [props.emptyText=""] - Text displayed if there are no queries.
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
      currentQueryIndex: 0,
      queries: this.props.queries
    };
    this.state.queries.forEach((ex) => ex.editedQuery = ex.query);

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
   * Getter method which returns the currently active query
   */
  get currentQuery() {
    return this.state.queries[this.state.currentQueryIndex];
  }
  // May set the current query by either title or index
  /**
   * Setter method to set the currently active query.
   *
   * @param {String|Number} value - If of type String, it sets the query based on title. If of type Number, it sets the query based on index.
   */
  set currentQuery(value) {
    if (typeof value === "string") {
      for (let i=0;i<this.state.queries.length;i++) {
        let query = this.state.queries[i];
        if (query.title === value) {
          value = i;
          break;
        }
      }
    }
    this.setState({ currentQueryIndex : value });
  }
  componentWillReceiveProps(newProps) {
    let addQueries = [];
    for (let i=0;i<newProps.queries.length;i++) {
      let newQuery = newProps.queries[i];
      // If every current query does not have the same exact title and body, it is new.
      if (this.state.queries.every(query => query.title !== newQuery.title && query.query !== newQuery.query)) {
        newQuery.editedQuery = newQuery.query;
        addQueries.push(newQuery);
      }
    }
    if (addQueries.length > 0) {
      this.setState({ queries : this.state.queries.concat(addQueries) });
    }
  }
  render() {
    return (
      <Modal show={this.state.show}
             onHide={this.hide}
             dialogClassName="queries-modal-dialog"
             className="queries-modal">
        <Modal.Header closeButton>
          <Modal.Title>
            {this.props.title}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body ref={this._modalBody}>
          <ReactTooltip place="right"/>
          <Container fluid={true} className="container">
            {
            this.currentQuery !== undefined ?
            <Row style={{flexWrap:"nowrap",height:"100%"}}>
              <ListGroup className="query-list">
                {
                  this.state.queries.map((query, i) => {
                    return (
                      // On click, set the current query and scroll back to the top
                      <ListGroup.Item active={this.state.currentQueryIndex===i} action onClick={() => {this.currentQuery = i;this._modalBody.current.scrollTop = 0;}}>
                        {query.title}
                      </ListGroup.Item>
                    );
                  })
                }
                {/* This empty item is in order to add a border to the entire list group */}
                {/*<ListGroup.Item />*/}
              </ListGroup>
              <div className="right-container">
                <div className="query-title-container">
                  {
                    (() => {
                      const title = this.currentQuery.title + (this.currentQuery.editedQuery !== this.currentQuery.query ? " (edited)" : "");
                      return <span className="query-title" title={title}>{title}</span>;
                    })()
                  }
                  <div className="query-button-container">
                    <FaPlay data-tip="Run the query" onClick={(e) => this.props.setActiveCallback(this.currentQuery.editedQuery, e)}/>
                    <FaUndo data-tip="Reset the query" onClick={() => {
                      this.currentQuery.editedQuery = this.currentQuery.query;
                      this.setState({ queries : this.state.queries });
                    }}/>
                  </div>
                </div>
                <CodeMirror className="query-modal-code"
                            value={this.currentQuery.editedQuery}
                            onBeforeChange={(editor,data,code) => {
                              this.currentQuery.editedQuery = code;
                              this.setState({ queries : this.state.queries });
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
            : this.props.emptyText
            }
          </Container>
        </Modal.Body>
      </Modal>
    );
  }
}
