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
   * @param {Object[]} props.queries - Array of query objects which must adhere to the structure {`title`: React.Component|string, `query`: string}.
   *    NOTE: The query objects may also contain other arbitrary information such as identifiers as long as none are the property `_editedQuery,`
   *          a private property automatically added to the object.
   * @param {Function} props.runButtonCallback - Invoked when the run button is pressed. Passed the arguments code<String> and event<MouseEvent>
   * @param {React.Component|String} props.title - Title of the modal.
   * @param {React.Component|String} [props.emptyText=""] - Text displayed if there are no queries.
   * @param {React.Component[]} [props.tools=[]] - Additional tools to add to the toolbar.
   *    To add a tooltip to the tool, use the any react-tooltip properties.
   * @param {number|null} [props.runButtonIndex=0] - Change the index in which the run button is inserted into the tool array. To hide it, set this to null.
   * @param {number|null} [props.resetButtonIndex=1] - Change the index in which the reset button is inserted into the tool array. To hide it, set this to null.
   *
   */
  static defaultProps = {
    runButtonCallback: (code, e) => {},
    title: '',
    emptyText: '',
    tools: [],
    runButtonIndex: 0,
    resetButtonIndex: 1
  };
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
    this.state.queries.forEach((ex) => ex._editedQuery = ex.query);

    this.show = this.show.bind (this);
    this.hide = this.hide.bind (this);

    this._modalBody = React.createRef();

    this._getTools = this._getTools.bind(this);
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
  /**
   * Returns the tools in formatted form.
   *
   * @private
   * @returns {React.Component[]} - The tools in formatted form.
   */
  _getTools() {
    let tools = this.props.tools.slice(); // Clone it
    const runButton = <FaPlay data-tip="Run the query" onClick={(e) => this.props.runButtonCallback(this.currentQuery._editedQuery, e)}/>
    const resetButton = (<FaUndo data-tip="Reset the query" onClick={() => {
      this.currentQuery._editedQuery = this.currentQuery.query;
      this.setState({ queries : this.state.queries });
    }}/>);
    // Insert the default tools
    if (this.props.runButtonIndex !== null) {
      tools.splice(this.props.runButtonIndex,0,runButton);
    }
    if (this.props.resetButtonIndex !== null) {
      tools.splice(this.props.resetButtonIndex,0,resetButton);
    }
    return tools;
  }
  /**
   * This should probably be replaced but it's very uninuitive to have to manually set the queries via ref.
   */
  componentWillReceiveProps(newProps) {
    let addQueries = newProps.queries;
    for (let i=0;i<addQueries.length;i++) {
      let newQuery = addQueries[i];
      let oldQuery = this.state.queries.filter(oldQuery => oldQuery.title === newQuery.title && oldQuery.query === newQuery.query);
      if (oldQuery.length === 0) {
        newQuery._editedQuery = newQuery.query;
      }
      else {
        newQuery._editedQuery = oldQuery[0]._editedQuery;
      }
    }
    this.setState({ queries : addQueries });
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
                      const title = this.currentQuery.title + (this.currentQuery._editedQuery !== this.currentQuery.query ? " (edited)" : "");
                      return <span className="query-title" title={title}>{title}</span>;
                    })()
                  }
                  <div className="query-button-container">
                    {
                      this._getTools()
                    }
                  </div>
                </div>
                <CodeMirror className="query-modal-code"
                            value={this.currentQuery._editedQuery}
                            onBeforeChange={(editor,data,code) => {
                              this.currentQuery._editedQuery = code;
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
