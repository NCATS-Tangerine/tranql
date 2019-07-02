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
      ','
    ];
    const selectorTokens = [
      "nodes",
      "links",
      "*"
    ];
    text = text.replace(/\s/g, "");
    const transitionRegex = transitionTokens.map(s=>s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|");
    // This prevents anything that could technically be a selector inside of selector attributes being matched as a new selector
    // Explanation:
    //    Group 1 - Join all selectors with or operators (and sanitize them for regex).
    //    Group 2 - Optionally match open and closing curly braces and anything inside of them.
    //    Group 3 - Lookahead and match either any transition or an end of line.
    const selectorRegex = new RegExp(`(${selectorTokens.map(s=>s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|")})({.*?})?(${transitionRegex}|$)`,"gi");
    let selectors = [];
    let selector;
    while (selector = selectorRegex.exec(text)) {
      selectors.push({
        selectorType : selector[1],
        selectorAttributes: selector[2],
        transition: selector[3]
      });
    }

    // const selectors = text.split(new RegExp(transitionRegex));
    // let transitions = text.match(new RegExp(transitionRegex,"g"));
    // if (transitions === null) {
    //   transitions = [];
    // }

    // console.log(selectors,transitions,selectorRegex,text);
    return selectors;
    // return {selectors, transitions};
  }
  /**
   * Parses an attribute (e.g. `type:"bar"`)
   *
   * @param {String[]} attribute - Attribute in form [`attributeName`, `attributeValue`]
   *
   * @returns {Array<String,Function|String>|Number} - Either an error code or an array of `attributeName`, `flagCallback`, and `attributeValue`.
   *    If `flagCallback` is of type string, the attribute does not contain a custom flag name, but does contain a flag.
   *
   */
  static parseAttribute(attribute) {
    // Custom attribute flags (e.g. `type:foo("bar")`)
    const flags = {
      regex: function(elementValue, value) {
        try {
          return elementValue.match(value);
        }
        catch (e) {
          return false;
        }
      }
    };

    let [attributeName, attributeValue] = attribute;

    let parsedAttribute = [
      attributeName,
      // Loose form of comparison that works with lists and objects as well
      (ev,v)=>JSON.stringify(v)===JSON.stringify(ev),
      attributeValue
    ];

    let flag = attributeName.match(/(?<=:)(?<!\\:).*/);
    if (flag !== null) {
      flag = flag[0];

      attributeName = attributeName.match(/.*(?=:)(?!\\:)/)
      // Update the attribute name to be the actual attribute name (without the flag)
      parsedAttribute[0] = attributeName;

      if (flags.hasOwnProperty(flag)) {
        parsedAttribute[1] = flags[flag];
      }
      else {
        // console.warn(`Invalid attribute flag with name "${flag}"`);
        parsedAttribute[1] = flag;
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
    const selectors = FindTool.parse(this._input.current.value);

    const graph = this.props.graph;

    for (let i=0;i<selectors.length;i++) {
      const {selectorType: selectorType, selectorAttributes: attributes, transition: transition} = selectors[i];
      const nextSelector = selectors[i+1];

      // Even
      if (i % 2 === 0) {

      }

      // const transition = transitions[i];

      if (selectors.length > 1 && nextSelector === undefined) {
        continue;
      }

      // let selectorType = selector.match(/[^\{]*/);
      // let attributes = selector.match(/\{(.*?)\}/g);

      // Special case - if no dict is provided it will use all instead of none. E.g. `nodes` will select all nodes, but `nodes{}` will select none.
      let useAll = false;

      // No attributes
      if (attributes === undefined) {
        attributes = {};
        useAll = true;
      }
      else {
        try {
          // Invalid
          attributes = JSON.parse(attributes);
        }
        catch (e) {
          return empty;
        }
      }
      let elements = {
        nodes: [],
        links: []
      }
      if (selectorType === "links") {
        elements.links = graph.links;
      }
      else if (selectorType === "nodes") {
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

      const addElem = (elementType,element) => {
        results[elementType].push(
          element.hasOwnProperty('origin') ? element.origin : element
        );
      }

      Object.keys(elements).forEach((elementType) => {
        elements[elementType].forEach((element) => {
          if (useAll) {
            addElem(elementType,element);
          }
          else {
            Object.entries(attributes).forEach((obj) => {
              let [attributeName, flagCallback, attributeValue] = FindTool.parseAttribute(obj);
              if (element.hasOwnProperty(attributeName)) {
                if (typeof flagCallback === "string") {
                  let flag = flagCallback;
                  flagCallback = function(elementValue, value) {
                    if (typeof elementValue[flag] === "function") {
                      try {
                        return elementValue[flag](value);
                      }
                      catch (e) {
                        return false;
                      }
                    }
                  }
                }
                if (flagCallback(element[attributeName],attributeValue)) {
                  addElem(elementType,element);
                }
                else {
                  console.log(element[attributeName],attributeValue);
                }
              }
            });
          }
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
