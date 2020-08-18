import React, { Component, useState } from 'react';
import { Button } from 'react-bootstrap';
import elasticlunr from 'elasticlunr';
import { debounce } from './Util.js';
import './FindTool2.css';

export default class FindTool2 extends Component {
  constructor(props) {
    super(props);

    this.state = {
      active: false,
      search: ""
    };

    this._results = this._results.bind(this);
    this._setInput = debounce(this._setInput.bind(this), 300);

    this._input = React.createRef();
  }
  _results() {
    const input = this.state.search;
    // If there's no input don't display the results and waste time building an entire search index
    if (input === "") return null;
    const searchIndex = elasticlunr(function() {
      // Nodes
      this.addField("name");
      this.addField("equivalent_identifiers");

      // Edges
      this.addField("source_id");
      this.addField("target_id");
      this.addField("predicate_id");
      this.addField("description");

      // Neutral
      this.addField("id");
      this.addField("type");

      // This property should uniquely identify a result among nodes and edges - cannot be an array/object
      this.setRef("index_identifier");
    });
    let identifier = 0;
    const identifierIndex = {}; // store nodes/edges for each index_identifier

    const NODE = 0;
    const LINK = 1;
    function addToDoc(nodeOrLink, type) {
      // Get current identifier and post-inc identifier
      const currentId = identifier++;
      identifierIndex[currentId] = {type: type, element: nodeOrLink};
      searchIndex.addDoc({
        index_identifier: currentId,
        ...nodeOrLink.origin
      });
    }
    this.props.graph.nodes.forEach((node) => addToDoc(node, NODE));
    this.props.graph.links.forEach((link) => addToDoc(link, LINK));
    const results = searchIndex.search(input, {
      expand: true
    });
    // console.log(results);
    // const results = this.props.graph.nodes.filter((node) => node.id.includes(input));
    const Results = () => {
      const resultsPerPage = 10;
      const [pages, setPages] = useState(1);
      const getNumResults = () => Math.min(results.length, pages * resultsPerPage);
      return (
        <div className="find-tool-result-container">
          <div className="find-tool-result find-tool-result-header">Showing {getNumResults()} of {results.length} results</div>
          {
            results.slice(0, getNumResults()).map((match, i) => {
              const { type, element } = identifierIndex[match.ref];
              const origin = element.origin;

              return (
                <Result resultMouseEnter={() => this.props.resultMouseEnter(element)}
                        resultMouseLeave={() => this.props.resultMouseLeave(element)}
                        key={i}>
                  {
                    type === NODE ? (
                      origin.hasOwnProperty("name") ? `${origin.name} (${origin.id})` : origin.id
                    ) : (
                      origin.source_id + "-[" + (Array.isArray(origin.type) ? origin.type : [origin.type]).join(", ") + "]->" + origin.target_id
                    )
                  }
                </Result>
              );
            })
          }
          {
            getNumResults() < results.length && (<div className="w-100 d-flex justify-content-center align-items-center">
              <Button variant="link" onClick={() => setPages(pages + 1)}>Show more</Button>
            </div>)
          }
        </div>
      );
    }
    return <Results/>
  }
  _setInput() {
    this.state.active && this.setState({ search : this._input.current.value });
  }
  show() {
    this.setState({ active : true }, () => {
      this._input.current.focus();
    });
  }
  hide() {
    this.setState({ active : false, search : "" });
  }
  toggleShow() {
    this.state.active ? this.hide() : this.show();
  }
  render() {
    if (!this.state.active) return null;

    return (
      <div className="FindTool">
        <input className="find-tool-input" autoFocus placeholder="Search:" ref={this._input} type="text" onInput={this._setInput}/>
        {this._results()}
      </div>
    );
  }
}

/* This class is basically just a glorified div element.
   It had to be turned into a class in order to use componentWillUnmount
   which is necessary to make sure  a highlighted element gets unhighlighted  */
class Result extends Component {
  constructor(props) {
    super(props);
  }
  componentWillUnmount() {
    this.props.resultMouseLeave();
  }
  render() {
    return (
      <div className="find-tool-result"
           onMouseEnter={this.props.resultMouseEnter}
           onMouseLeave={this.props.resultMouseLeave}>
        {this.props.children}
      </div>
    );
  }
}
