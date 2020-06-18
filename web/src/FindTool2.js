import React, { Component } from 'react';
import elasticlunr from 'elasticlunr';
import './FindTool2.css';

export default class FindTool2 extends Component {
  constructor(props) {
    super(props);

    this.state = {
      active: false,
      search: ""
    };

    this._results = this._results.bind(this);

    this._input = React.createRef();
  }
  _results() {
    const input = this.state.search;
    const nodeIndex = elasticlunr(function() {
      this.addField("id");
      this.addField("name");
      // this.addField("reasoner");
      this.addField("type");
      this.setRef("id");
    });
    this.props.graph.nodes.forEach((node) => nodeIndex.addDoc(node));
    const results = nodeIndex.search(input, {
      bool: "OR"
    });
    console.log(results);
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
  show() {
    this.setState({ active : true }, () => {
      this._input.current.focus();
    });
  }
  hide() {
    this.setState({ active : false });
  }
  toggleShow() {
    this.state.active ? this.hide() : this.show();
  }
  render() {
    if (!this.state.active) return null;

    return (
      <div className="FindTool">
        <span contentEditable={true} className="find-tool-input" autoFocus placeholder="Search:" ref={this._input} onInput={() => {
          this.setState({ search : this._input.current.textContent });
        }}/>
        <div className="find-tool-result-container">
          {this._results()}
        </div>
      </div>
    );
  }
}
