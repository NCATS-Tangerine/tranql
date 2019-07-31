import React, { Component } from 'react';
import { IoIosClose, IoIosSettings } from 'react-icons/io';
import { FaLongArrowAltRight, FaLongArrowAltLeft } from 'react-icons/fa';
import * as JSON5 from 'json5';
import * as jp from 'jsonpath';
import { debounce, hydrateState } from './Util.js';
import './FindTool.css';

export default class FindTool extends Component {
  static defaultProps = {
    resultMouseEnter: ()=>{},
    resultMouseLeave: ()=>{},
    resultMouseClick: ()=>{}
  };
  constructor(props) {
    super(props);

    this.state = {
      active: false,
      results: null,
      entered: null,
      showSettings: false,
      useJSONPath: false
    };

    this.toggleShow = this.toggleShow.bind(this);
    this.show = this.show.bind(this);
    this.hide = this.hide.bind(this);

    this._onKeyDown = this._onKeyDown.bind(this);
    this._onInputBlur = this._onInputBlur.bind(this);
    this._onInput = this._onInput.bind(this);

    this._hydrateState = hydrateState.bind(this);

    this._findResults = this._findResults.bind(this);
    this._results = this._results.bind(this);
    this.updateResults = this.updateResults.bind(this);
    this.showSettings = this.showSettings.bind(this);

    this._setDefaultJSONPathQuery = this._setDefaultJSONPathQuery.bind(this);

    this._input = React.createRef();

    this._inputHandler = debounce(this._onInput,300);
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
  showSettings() {
    this.setState({
      showSettings : true
    });
  }
  _onInput(e) {
    this.state.entered !== null && this.props.resultMouseLeave(this.state.entered);
    this.setState({ entered : null });
    this.updateResults();
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
  _setDefaultJSONPathQuery() {
    if (this._input.current.textContent === "") {
      this._input.current.textContent = "$.*";
      // Update cursor position (required with contenteditable elements)
      let range = document.createRange();
      range.selectNodeContents(this._input.current);
      range.collapse(false);
      let selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
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
    // text = text.replace(/\s/g, "");
    const transitionRegex = transitionTokens.map(s=>s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|");
    // This prevents anything that could technically be a selector inside of selector attributes being matched as a new selector
    // Explanation:
    //    Group 1 - Join all selectors with or operators (and sanitize them for regex).
    //    Group 2 - Optionally match open and closing curly braces and anything inside of them (e.g. `{foo}`).
    //    Group 3 - Match either any transition or an end of line.
    const selectorRegex = new RegExp(`(${selectorTokens.map(s=>s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|")})({.*?})?(${transitionRegex}|$)`,"gi");
    let selectors = [];
    let selector;
    while ((selector = selectorRegex.exec(text))) {
      selectors.push({
        selectorType : selector[1],
        selectorAttributes: selector[2],
        transition: selector[3]
      });
    }
    let skipNextIter = 0;
    selectors = selectors.reduce((acc, sel, i) => {
      if (skipNextIter > 0) {
        skipNextIter--;
        return acc;
      }
      if (sel.transition !== "") {
        const transitionSelector = selectors[i+1];
        const nextSelector = selectors[i+2];
        // Make sure that we don't have a case where no selector is present but a transition is (e.g. `nodes{"foo":"bar"}->`). Treat it as if there is no transition if there is no selector.
        if (nextSelector !== undefined) {
          sel.transitionSelector = transitionSelector;
          sel.nextSelector = nextSelector
          if (nextSelector.transition === "")  {
            // If the nextSelector does not have a transition do not include it as a general selector (e.g. just `nodes{"foo":"bar"}`) because it is only intended to be for this transition.
            skipNextIter++;
          }
          skipNextIter++;
        }
      }
      acc.push(sel);
      return acc;
    }, []);
    if (selectors.length === 0) {
      return "No valid selectors found";
    }
    if (selectors.length % 2 === 0) {
      return "Invalid selector or transition";
    }
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
      // Tests a regex pattern against the value
      "regex": function(elementValue, value) {
        try {
          return elementValue.match(value);
        }
        catch {
          return false;
        }
      },
      // Run a given function on the attribute
      "func": function(elementValue, value) {
        // This allows for unrestrained access of the object but is not recommended unless necessary.
        try {
          if (typeof value === "string") {
            // Sadly, it's necessary to use eval here. It doesn't really pose as a threat here as long as find tool input is never cached.
            // eslint-disable-next-line
            value = eval(value);
          }
          return value(elementValue);
        }
        catch {
          return false;
        }
      },
      "<": function(elementValue, value) {
        // Performs < operator on the provided values
        try {
          return elementValue < value
        }
        catch {
          return false;
        }
      },
      ">": function(elementValue, value) {
        // Performs > operator on the provided values
        try {
          return elementValue > value
        }
        catch {
          return false;
        }
      },
      "<=": function(elementValue, value) {
        // Performs <= operator on the provided values
        try {
          return elementValue <= value
        }
        catch {
          return false;
        }
      },
      ">=": function(elementValue, value) {
        // Performs >= operator on the provided values
        try {
          return elementValue >= value
        }
        catch {
          return false;
        }
      },
      "!==": function(elementValue, value) {
        // Performs !== operator on the provided values (default operator is ===)
        try {
          return elementValue !== value
        }
        catch {
          return false;
        }
      },
      "!=": function(elementValue, value) {
        // Performs != operator on the provided values (default operator is ===)
        try {
          // (eslint complains about non eqeqeq)
          // eslint-disable-next-line
          return elementValue != value
        }
        catch {
          return false;
        }
      },
      "===": function(elementValue, value) {
        // Performs === operator on the provided values (completely redundant but present for comprehensiveness)
        try {
          return elementValue === value
        }
        catch {
          return false;
        }
      },
      "==": function(elementValue, value) {
        // Performs == operator on the provided values (default operator is ===)
        try {
          // (eslint complains about non eqeqeq)
          // eslint-disable-next-line
          return elementValue == value
        }
        catch {
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

    let flag = attributeName.match(/[^\\:][:](.*)/);

    if (flag !== null) {
      flag = flag[1];

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
  static parseAttributesString(attributes) {
    // Special case - providing no dict is a shorthand for saying `{selector}{}`, which selects everything from that selector (e.g. `nodes{}` or `nodes` will select all nodes)
    if (attributes === undefined) {
      attributes = {};
    }
    else {
      try {
        // Invalid
        attributes = JSON5.parse(attributes);
      }
      catch (e) {
        return "Invalid attribute syntax";
      }
    }
    return attributes;
  }
  static handleSelector(graph, selector, attribs={}, magicVariables={}) {
    const results = {
      nodes: [],
      links: []
    };
    const { selectorType, transition, transitionSelector, nextSelector } = selector;
    let { selectorAttributes: attributes } = selector;
    // console.log(selectors);
    // nodes{"type:includes":"drug_exposure"}->links{}->nodes{"type:includes":"chemical_substance"}

    attributes = FindTool.parseAttributesString(attributes);
    if (typeof attributes === "string") {
      return attributes + ` for selector "${selectorType}"`;
    }

    attributes = {...attributes, ...attribs};

    let elements = FindTool.findElems(graph, selectorType, attributes, transition, transitionSelector, nextSelector, magicVariables);

    if (typeof elements === "string") {
      return elements;
    }
    else {
      results.nodes = results.nodes.concat(elements.nodes);
      results.links = results.links.concat(elements.links);
    }

    // If nextSelector is defined, that means that this is a node pair and therefore has a link transition.
    if (nextSelector) {
      // We want to add the results of the next selector first. Then we can take any links with a source id of any nodes from the first selector and a target id of any nodes from the last selector.
      let {nextSelector: nextSelectorNextSelector, ...nextSel} = nextSelector;
      let nextSelResults = FindTool.handleSelector(graph, nextSel);

      if (typeof nextSelResults === "string") {
        return nextSelResults;
      }

      let transitionAttributes = {};
      let source_re;
      let target_re;
      if (transition === "->") {
        // Compile regex that matches any nodes with a source id of any nodes in the first selector and a target id of any nodes in the second selector
        source_re = new RegExp(results.nodes.map((n)=>n.id).join("|"));
        target_re = new RegExp(nextSelResults.nodes.map((n)=>n.id).join("|"));
        if (results.nodes.length === 0 || nextSelResults.nodes.length === 0) {
          return (
            {
              nodes:[],
              links:[]
            }
          )
        }
        transitionAttributes = {
          "source_id:regex":source_re,
          "target_id:regex":target_re
          // "origin:func": `(origin)=>origin.source_id.match(${source_re}) && origin.target_id.match(${target_re})`
        };
      }
      let nextTransitionResults = FindTool.handleSelector(graph, transitionSelector, transitionAttributes, {
        "__sourceNodes__" : source_re,
        "__targetNodes__" : target_re
      });
      if (typeof nextTransitionResults === "string") {
        return nextTransitionResults;
      }
      // Nodes should always be empty here but it is here anyways for consistency.
      results.nodes = results.nodes.concat(nextTransitionResults.nodes);
      results.links = results.links.concat(nextTransitionResults.links);

      // Links should always be empty here but it is here anyways for consistency.
      results.nodes = results.nodes.concat(nextSelResults.nodes);
      results.links = results.links.concat(nextSelResults.links);

      // Filter out any nodes which do not have any links connecting them
      results.nodes = results.nodes.filter((node) => {
        return results.links.reduce((acc,link) => {
          return link.source_id === node.id || link.target_id === node.id ? acc + 1 : acc;
        },0);
      });

      // Filter out any duplicate nodes
      let nodeIds = [];
      results.nodes = results.nodes.filter((node) => {
        if (!nodeIds.includes(node.id)) {
          nodeIds.push(node.id);
          return true;
        }
        return false;
      });

      // Filter out any links whose nodes are not present in the result (because it uses regex to select links it also tends to match substrings)
      results.links = results.links.filter((link) => {
        return nodeIds.includes(link.source_id) && nodeIds.includes(link.target_id);
      });
    }

    return results;
  }
  static repr(obj) {
    let primitive = false;
    let str;
    if (Array.isArray(obj)) {
      // Array
      str = "[" + obj.length + "]";
    }
    else if (obj.constructor.name === "Object") {
      // Object literal
      str = "{" + Object.keys(obj).length + "}";
    }
    else if (obj === Object(obj)) {
      // Not primitive or object literal or array
      str = obj.constructor.name;
    }
    else {
      // Primitive
      str = obj.toString();
      primitive = true;
    }
    return {value: str, primitive: primitive};
  }
  static findElems(graph, selectorType, attributes, transition, transitionSelector, nextSelector, magicVariables) {
    let elements = {
      nodes: [],
      links: []
    };
    let results = {
      nodes: [],
      links: []
    };
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
      return `Invalid selector type "${selectorType}"`;
    }


    const addElem = (elementType,element) => {
      results[elementType].push(
        element
      );
    }

    magicVariables["__nodes__"] = JSON.stringify(graph.nodes);
    magicVariables["__links__"] = JSON.stringify(graph.links,(key,val)=>key!=="allConnections"?val:undefined);

    Object.keys(elements).forEach((elementType) => {
      elements[elementType].forEach((element) => {
        element = element.origin;
        let every = Object.entries(attributes).every((obj) => {
          let [attributeName, flagCallback, attributeValue] = FindTool.parseAttribute(obj);
          if (element.hasOwnProperty(attributeName)) {
            if (typeof flagCallback === "string") {
              let flag = flagCallback;
              flagCallback = function(elementValue, value) {
                // If the flag is a method of the value
                if (typeof elementValue[flag] === "function") {
                  try {
                    return elementValue[flag](value);
                  }
                  catch (e) {
                    return false;
                  }
                }
                else {
                  // If the flag is an attribute of the value (as opposed to a method)
                  return elementValue[flag] === value
                }
              }
            }
            magicVariables["__element__"] = JSON.stringify(element,(key,val)=>key!=="allConnections"?val:undefined);
            // Replace any magic variables
            let re = /[^\\](__.*?__)/g;
            let sel;
            while ((sel = re.exec(attributeValue))) {
              attributeValue = attributeValue.replace(sel[1],(val) => magicVariables[val]);
            }
            // if (typeof attributeValue === "string") attributeValue = attributeValue.replace(, (val) => magicVariables[val]);
            return flagCallback(element[attributeName],attributeValue);
          }
          return false;
        });
        if (every) {
          addElem(elementType,element);
        }
      });
    });
    return results;
  }
  _findResults() {
    // Results stores the results of each transition
    const results = {
      nodes:[],
      links:[]
    };

    // const replaceNodes = this.props.graph.nodes;
    // const replaceLinks = this.props.graph.links.map((link) => {
    //   // Remove circular objects.
    //   return Object.assign({}, link, { allConnections : undefined });
    // });
    // let graph = JSON.parse(JSON.stringify({
    //   nodes:replaceNodes,
    //   links:replaceLinks
    // }));
    let graph = this.props.graph;

    const val = this._input.current === null ? "" : this._input.current.textContent;

    if (this.state.useJSONPath) {
      let results = [];
      let graphElement = false;
      try {
        results = jp.nodes({nodes:graph.nodes,links:graph.links},val).map((el) => {
          // Must be a node or link object
          if (el.path.length === 3) {
            graphElement = true;
            return el;
          }
          return el;
        });
      }
      catch {}
      return {
        grouped: false,
        groups: results,
        graphElement: graphElement
      }
    }

    const selectors = FindTool.parse(val);
    if (typeof selectors === "string") {
      return selectors;
    }


    let anyTransitions = false;

    for (let i=0;i<selectors.length;i++) {
      let selector = selectors[i];
      let elems = FindTool.handleSelector(graph, selector);
      if (typeof elems === "string") {
        return elems;
      }
      results.nodes = results.nodes.concat(elems.nodes);
      results.links = results.links.concat(elems.links);

      if (selector.transition !== "") {
        anyTransitions = true;
      }
    }

    let grouped = [];

    let nodeMap = {};
    results.nodes.forEach((node) => {
      nodeMap[node.id] = node;
    });
    if (!anyTransitions) {
      return {
        grouped : false,
        groups: [
          ...graph.nodes.filter((node)=>nodeMap.hasOwnProperty(node.origin.id)),
          ...results.links.map((link)=>graph.links.filter((link_2)=>link_2.origin===link)[0])
        ].map((el)=>({value:el}))
        // groups: [...results.nodes, ...results.links].map((el)=>({value:el}))
      };
    }
    else {
      results.links.forEach((link) => {
        grouped.push({
          source: nodeMap[link.source_id],
          target: nodeMap[link.target_id],
          link: graph.links.filter((link_2)=>link_2.origin===link)[0]
        });
      });

      return {
        grouped: true,
        groups: grouped
      };
    }

  }
  _results() {
    const results = this._findResults();
    let elements;
    if (typeof results === "string") {
      // Error
      elements = (
        <div>
          <div className="find-tool-result find-tool-result-header">
            <span style={{fontWeight:"500"}}>{results}</span>
          </div>
        </div>
      );
    }
    else {
      elements = (
        <div>
          <div className="find-tool-result find-tool-result-header">
            {
              (() => {
                let invalid;

                let jsonPathComp;

                let path_on_render;
                try {
                  if (this._input.current.textContent === '') {
                    path_on_render = [];
                  }
                  else {
                    path_on_render = jp.parse(this._input.current.textContent);
                  }
                }
                catch (e) {
                  path_on_render = [];
                  if (this.state.useJSONPath) invalid = e.message;
                }
                if (!results.grouped && this.state.useJSONPath) jsonPathComp = (
                  <div className="find-tool-back-button-wrapper">
                  <FaLongArrowAltLeft className="find-tool-back-button" style={{...(path_on_render.length < 2 ? {display:"none"} : {})}} onClick={() => {
                    // Remove the second to last path component from the query
                    // If the path is only one level deep (`$.*`), remove the last because there is no second to last path component.
                    const path = jp.parse(this._input.current.textContent);
                    console.log(path,path.length);
                    const newPath = path.length > 2 ? path.slice(0,-2).concat(path.slice(-1)) : path.slice(0,-1);
                    this._input.current.textContent = jp.stringify(newPath)
                    this._inputHandler();
                  }}/>
                  </div>
                )

                return (
                  <>
                    {!invalid && jsonPathComp}
                    <span style={{fontWeight:"500"}}>
                    {
                      invalid ?
                        invalid :
                        (results.groups.length + " results")
                    }
                    </span>
                  </>
                );
            })()
            }
          </div>
          {
            results.groups.map((group, i) => {
              let value = (results.grouped ? Object.values(group) : [group.value]);
              return (
                <div className="find-tool-result"
                     onMouseEnter={()=>{
                       if (results.hasOwnProperty('graphElement') && !results.graphElement) return;
                       this.setState({ entered : value });
                       this.props.resultMouseEnter(value);
                     }}
                     onMouseLeave={()=>{
                       if (results.hasOwnProperty('graphElement') && !results.graphElement) return;
                       this.setState({ entered : null });
                       this.props.resultMouseLeave(value);
                     }}
                     onClick={()=>{
                       this.props.resultMouseClick(value);
                     }}
                     key={i}>
                  {
                    results.grouped ?
                      <>
                        <div className="result-group"><span>{group.source.name}</span><span>{" (" + group.source.id + ")"}</span></div>
                        <div className="group-arrow"><FaLongArrowAltRight/></div>
                        <div className="result-group"><span>{(Array.isArray(group.link.type) ? group.link.type : [group.link.type]).join(" / ")}</span></div>
                        <div className="group-arrow"><FaLongArrowAltRight/></div>
                        <div className="result-group"><span>{group.target.name}</span><span>{" (" + group.target.id + ")"}</span></div>
                      </> :
                        <div>
                          {
                            (() => {
                              let repr;
                              // group.value was once undefined, couldn't recreate it but just to be safe
                              try {
                                repr = FindTool.repr(group.value);
                              }
                              catch {
                                repr = ['<Error>',true]
                                console.warn('Group value broken',group);
                              }
                              return (
                                <>
                                  <div className="result-group">
                                    <span>
                                    {
                                      (!results.hasOwnProperty('graphElement') || results.graphElement) ? (
                                        group.value.hasOwnProperty('name') ?
                                          group.value.name :
                                          (Array.isArray(group.value.type) ? group.value.type : [group.value.type]).join(" / ")
                                      ) :
                                      group.path[group.path.length-1] + ": "
                                    }
                                    </span>
                                    <span>
                                    {
                                      (!results.hasOwnProperty('graphElement') || results.graphElement) ? (
                                        (group.value.hasOwnProperty('id') ? " (" + group.value.id + ")" : "")
                                      ) :
                                      repr.value
                                    }
                                    </span>
                                  </div>
                                  {
                                    this.state.useJSONPath && !repr.primitive && (
                                      <div className="find-tool-select-button-wrapper">
                                      <FaLongArrowAltRight className="find-tool-select-button" onClick={() => {
                                        this._input.current.textContent = jp.stringify(group.path) + ".*";
                                        this._inputHandler();
                                      }}/>
                                      </div>
                                    )
                                  }
                                </>
                              );
                            })()
                          }
                        </div>
                  }
                </div>
              );
            })
          }
        </div>
      );
    }
    return elements;
  }
  updateResults() {
    this.setState({ results : this._results() });
  }
  componentWillUnmount() {
    window.removeEventListener('keydown',this._onKeyDown);
    this._input.current.removeEventListener('blur', this._onInputBlur);
    this._input.current.removeEventListener('input',this._inputHandler);
    this.state.entered !== null && this.props.resultMouseLeave(this.state.entered);
  }
  componentDidMount() {
    window.addEventListener('keydown',this._onKeyDown);
    this._input.current.addEventListener('blur', this._onInputBlur);
    this._input.current.addEventListener('input',this._inputHandler);

    this._hydrateState();

    this.setState({},() => {
      this.state.useJSONPath && this._setDefaultJSONPathQuery();
    });

    this.updateResults();
  }
  render() {
    return (
      <div data-hide={!this.state.active} className="FindTool">
        <div data-hide={this.state.showSettings} className="find-container">
          <span contentEditable={true} ref={this._input} className="find-tool-input" autoFocus placeholder={this.state.useJSONPath ? "JSONPath ($):" : "Query:"}></span>
          <div className="find-tool-button-container vertical-bar">
            <IoIosSettings className="find-tool-settings-button" onClick={() => this.showSettings()}/>
            <IoIosClose className="find-tool-close-button" onClick={() => this.hide()}/>
          </div>
        </div>
        <div data-hide={this.state.showSettings} className="find-tool-result-container">
          {
            this.state.results
          }
        </div>
        <div data-hide={!this.state.showSettings} className="find-tool-settings">
          <div className="find-tool-settings-top horizontal-bar">
            <span className="find-tool-settings-header">Find Tool Settings</span>
            <div className="find-tool-button-container vertical-bar">
              <IoIosClose className="find-tool-close-button" onClick={() => this.setState({ showSettings : false })}/>
            </div>
          </div>
          <div className="find-tool-settings-body">
            <div>
              <input type="checkbox"
                     name="useJSONPath"
                     checked={this.state.useJSONPath}
                     onChange={(e) => {
                       const name = e.currentTarget.name;
                       const checked = e.currentTarget.checked;
                       this.setState({
                         useJSONPath : checked
                       }, () => {
                         if (checked) {
                           this._setDefaultJSONPathQuery();
                         }
                         this.updateResults();
                       });
                       localStorage.setItem(name,JSON.stringify(checked));
                     }}/>
               <span>Use <a target="_blank" rel="noopener noreferrer" href="https://goessner.net/articles/JsonPath/">JSONPath</a> syntax</span>
            </div>
          </div>
        </div>
      </div>
    )
  }
}
