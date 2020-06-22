import React, { Component } from 'react';
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
    const searchIndex = elasticlunr(function() {
      // Nodes
      this.addField("name");
      // this.addField("equivalent_identifiers");

      // Edges
      this.addField("predicate_id");
      this.addField("description");

      // Neutral
      this.addField("id");
      // Type field breaks elasticlunr in schema view for whatever reason
      // this.addField("type");

      this.setRef("id");
    });
    this.props.graph.nodes.forEach((node) => searchIndex.addDoc(node.origin));
    this.props.graph.links.forEach((link) => searchIndex.addDoc(link.origin));
    const results = searchIndex.search(input, {});
    // console.log(results);
    // const results = this.props.graph.nodes.filter((node) => node.id.includes(input));
    return (
      <div>
        <div className="find-tool-result find-tool-result-header">{results.length} results</div>
        {
          results.map((match, i) => {
            return (
              <div className="find-tool-result" key={i}>
                {
                  match.ref
                }
              </div>
            );
          })
        }
      </div>
    );
  }
  _setInput() {
    this.setState({ search : this._input.current.textContent });
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
        <span contentEditable={true} className="find-tool-input" autoFocus placeholder="Search:" ref={this._input} onInput={this._setInput}/>
        <div className="find-tool-result-container">
          {this._results()}
        </div>
      </div>
    );
  }
}
