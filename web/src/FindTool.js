import React, { Component } from 'react';
import { IoIosClose } from 'react-icons/io';
import './FindTool.css';

export default class FindTool extends Component {
  constructor(props) {
    super(props);

    this.state = {
      active: false,
      results: null
    };

    this.toggleShow = this.toggleShow.bind(this);
    this.show = this.show.bind(this);
    this.hide = this.hide.bind(this);

    this._onKeyDown = this._onKeyDown.bind(this);
    this._onInputBlur = this._onInputBlur.bind(this);
    this._onInput = this._onInput.bind(this);

    this._findResults = this._findResults.bind(this);
    this._results = this._results.bind(this);

    this._input = React.createRef();
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
  _onInput(e) {
    this.setState({ results : this._results() });
  }
  _onKeyDown(e) {
    if (e.ctrlKey && e.keyCode === 70) {
      e.preventDefault();
      this.toggleShow();
    }
    // Escape key
    else if (this.state.active && e.keyCode === 27) {
      this.hide();
    }
  }
  _onInputBlur(e) {
    if (this.state.active) {
      // e.preventDefault();
      // this._input.current.focus();
    }
  }
  static parse(text) {
    const transitionTokens = [
      '->',
      '<-',
      '<->'
    ];
    text = text.replace(/\s/g, "");
    const transitionRegex = transitionTokens.join("|");
    const selectors = text.split(new RegExp(transitionRegex));
    let transitions = text.match(new RegExp(transitionRegex,"g"));

    if (transitions === null) {
      transitions = [];
    }

    return {selectors, transitions};
  }
  /**
   * Parses an attribute (e.g. `type:"bar"`)
   *
   * @param {String[]} attribute - Attribute in form [`attributeName`, `attributeValue`]
   *
   * @returns {<String,Object>[]|Number} - Either an error code or an array of `attributeName`, `attributeValue`, where attribute value is in the form {`value`, `flagCallback`}.
   *    If -1, the attribute contains an invalid flag name.
   *
   */
  static parseAttribute(attribute) {
    // Special attribute flags (e.g. `type:includes("bar")`)
    const flags = {
      "includes": function(elementValue, value) {
        return elementValue.includes(value);
      }
    };
    // Flag alisaes
    flags.contains = flags.includes;


    let [attributeName, attributeValue] = attribute;

    let parsedAttribute = [
      attributeName,
      {
        value: attributeValue,
        // Loose form of comparison that works with lists and objects as well
        flagCallback: (ev,v)=>JSON.stringify(v)===JSON.stringify(ev)
      }
    ];

    let flag = attributeName.match(/(?<=:)(?<!\\:).*/);
    if (flag !== null) {
      flag = flag[0];

      attributeName = attributeName.match(/.*(?=:)(?!\\:)/)
      // Update the attribute name to be the actual attribute name (without the flag)
      parsedAttribute[0] = attributeName;

      if (flags.hasOwnProperty(flag)) {
        parsedAttribute[1].flagCallback = flags[flag];
      }
      else {
        console.warn(`Invalid attribute flag with name "${flag}"`);
        return -1;
      }
    }

    return parsedAttribute;
  }
  _findResults() {
    const empty = {
      nodes: [],
      links: []
    };
    const results = {
      nodes: [],
      links: []
    };

    if (this._input.current === null) return results;
    const {selectors, transitions} = FindTool.parse(this._input.current.value);

    const graph = this.props.graph;

    for (let i=0;i<selectors.length;i++) {
      const selector = selectors[i];
      const nextSelector = selectors[i+1];
      const transition = transitions[i];

      if (selectors.length > 1 && nextSelector === undefined) {
        continue;
      }

      let selectorType = selector.match(/[^\{]*/);
      let attributes = selector.match(/\{(.*?)\}/g);

      // No attributes
      if (attributes === null) {
        attributes = {};
        selectorType = selector;
      }
      else {
        try {
          // Invalid
          attributes = JSON.parse(attributes);
        }
        catch (e) {
          return empty;
        }
        selectorType = selectorType[0];
      }
      let elements = {
        nodes: [],
        links: []
      }
      if (selectorType === "link" || selectorType === "l" || selectorType === "links") {
        elements.links = graph.links;
      }
      else if (selectorType === "node" || selectorType === "n" || selectorType === "nodes") {
        elements.nodes = graph.nodes;
      }
      else if (selectorType === "*") {
        elements.nodes = graph.nodes;
        elements.links = graph.links;
      }
      else {
        // Invalid selector type
        return empty;
      }

      console.log(selectorType,attributes);

      Object.keys(elements).forEach((elementType) => {
        elements[elementType].forEach((element) => {
          Object.entries(attributes).forEach((obj) => {
            let [attributeName, attributeValue] = FindTool.parseAttribute(obj);
            if (element.hasOwnProperty(attributeName)) {
              if (attributeValue.flagCallback(element[attributeName],attributeValue.value)) {
                results[elementType].push(
                  element.hasOwnProperty('origin') ? element.origin : element
                );
              }
              else {
                console.log(element[attributeName],attributeValue.value);
              }
            }
          });
        });
      });

      // if (transition === undefined) {
      //   graph.nodes.forEach((node) => {
      //
      //   });
      // }
      // else {
      //   graph.links.forEach((link) => {
      //
      //   });
      //   graph.nodes.forEach((node) => {
      //
      //   });
      // }
    }

    return results;
  }
  _results() {
    const results = this._findResults();
    const elements = Object.keys(results).map((elementType, i) => {
      return (
        <div key={i}>
          <h4>{elementType}</h4>
          {
            results[elementType].map((element, n) => {
              return (
                <div key={n}>
                  {JSON.stringify(element)}
                </div>
              )
            })
          }
        </div>
      )
    });
    return elements;
  }
  componentWillUnmount() {
    window.removeEventListener('keydown',this._onKeyDown);
    this._input.current.removeEventListener('blur', this._onInputBlur);
    this._input.current.removeEventListener('input',this._onInput);
  }
  componentDidMount() {
    window.addEventListener('keydown',this._onKeyDown);
    this._input.current.addEventListener('blur', this._onInputBlur);
    this._input.current.addEventListener('input',this._onInput);

    this.setState({ results : this._results() });
  }
  render() {
    return (
      <div data-hide={!this.state.active} className="FindTool">
        <div className="find-container">
          <input type="text" ref={this._input} className="find-tool-input" autoFocus />
          <div className="find-tool-button-container">
            <IoIosClose onClick={() => this.hide()}/>
          </div>
        </div>
        <div className="result-container">
          {
            this.state.results
          }
        </div>
      </div>
    )
  }
}
