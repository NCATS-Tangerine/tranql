import React, { Component } from 'react';
import { ButtonToolbar, ToggleButtonGroup, ToggleButton } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import './Legend.css';

// Method for darkening the shade of a hex string
//    source: https://stackoverflow.com/questions/5560248/programmatically-lighten-or-darken-a-hex-color-or-rgb-and-blend-colors
function shadeColor(color, percent) {
    //negative percent => darker

    var R = parseInt(color.substring(1,3),16);
    var G = parseInt(color.substring(3,5),16);
    var B = parseInt(color.substring(5,7),16);

    R = parseInt(R * (100 + percent) / 100);
    G = parseInt(G * (100 + percent) / 100);
    B = parseInt(B * (100 + percent) / 100);

    R = (R<255)?R:255;
    G = (G<255)?G:255;
    B = (B<255)?B:255;

    var RR = ((R.toString(16).length==1)?"0"+R.toString(16):R.toString(16));
    var GG = ((G.toString(16).length==1)?"0"+G.toString(16):G.toString(16));
    var BB = ((B.toString(16).length==1)?"0"+B.toString(16):B.toString(16));

    return "#"+RR+GG+BB;
}

// Legend button group component (TypeButton wrapper)
class TypeButtonGroup extends React.Component {
  constructor(props,context) {
    super(props,context);

    this._handleChange = this._handleChange.bind(this);

    this.state = {
      value:[...Object.keys(this.props.elementData).map((elementType,index) => {
        return {
          type:elementType,
          id:index,
          callback:this.props.elementData[elementType].callback
        };
      })]
    }
  }

  _handleChange(value,event) {
    // This is likely a poor method of going about this, but I could find no documentation on how to accomplish this simple task.
    // It probably shouldn't be this ridiculously complicated to do such a simple thing.
    let newValue = value[value.length-1];
    let newState = this.state.value.slice();
    let turnedOn = false;
    this.state.value.forEach((value,i) => {
      let num = value.id;
      if (num === newValue.id) {
        newState.splice(i,1);
      }
    });
    if (newState.length === this.state.value.length) {
      newState.push(newValue);
      turnedOn = true;
    }
    typeof newValue.callback === "function" && newValue.callback(newValue.type,newValue.elements,turnedOn); //call the callback and pass on/off to it
    this.setState({ value: newState });
  }

  render() {
    return (
      <ToggleButtonGroup
        type="checkbox"
        value={this.state.value}
        onChange={this._handleChange}
      >
        {
          Object.keys(this.props.elementData).map((elementType,n) => {
            // How to generate unique id??
            let checked = this.state.value.some(val => val.id === n);
            let data = {
              type: elementType,
              elements: this.props.elementData[elementType].elements
            };
            return <TypeButton value={{type:data.type,elements:data.elements,id:n,callback:this.props.elementData[elementType].callback}} active={checked} data={data} key={n} />
          })
        }
      </ToggleButtonGroup>
    );
  }
}

// Legend button component
class TypeButton extends Component {
  constructor(props) {
    super(props);
    this.state = {
      elements:this.props.data.elements,
      color:null,
      type: TypeButton.adjustTitle(this.props.data.type)
    };
  }

  static adjustTitle(title) {
    // NOTE: This method of splitting by underscore will lead to adverse effects if types can have natural underscores in them
    // (Can they?)
    let newTitle = title.split('_').join(' ');
    let capitalizedTitle = newTitle.charAt(0).toUpperCase() + newTitle.slice(1);
    return capitalizedTitle;
  }

  componentDidMount() {
    // Wait for color to be defined on this type
    //  (ForceGraph auto assigns colors to types asynchronously and lacks a callback for its completion)

    //HACK: ANY SUGGESTIONS WELCOME
    //  Spent a couple of hours attempting to find the best way to wait for the "color" property to be set by the ReactForceGraph, considering it does not provide any way to detect it;
    //  Could not find any better way than to simply brute force it by waiting.
    let int = setInterval(() => {
      let color = this.state.color;
      while (color === undefined || color === null) {
        let elements = this.state.elements;
        for (let i=0;i<elements.length;i++) {
          let element = elements[i];
          if (element.color !== undefined && element.color !== null) {
            // Color is now defined
            color = element.color;
            this.setState({color: color});
            clearInterval(int);
            break;
          }
        }
      }

    },50);
  }

  render() {
    //Bootstrap doesn't like custom coloring schemes, but it is necessary here to deviate from the bootstrap color theme as it is specifically color-coded.
    //When a react-bootstrap ToggleButton is active, it uses the box-shadow property as what looks like the "border." This is set as the property data-highlightColor,
    //so that it is only applied when active
    let style = {
      backgroundColor:this.state.color,
      '--highlight-color':shadeColor(this.state.color === null ? "#000000" : this.state.color,-15)
    };
    //Set var '--highlight-color' in inline style property to be accessed when focused

    //Better way of extending react component and passing on properties?
    return (
      <ToggleButton
        style={style}
        name={this.props.name}
        type={this.props.type}
        onChange={this.props.onChange}
        checked={this.props.active}
        value={this.props.value}
        size="sm"
        className="TypeButton">
        ({this.state.elements.length}) {this.state.type}
      </ToggleButton>
    );
  }
}


/**
  * Legend component for elements of the graph (nodes & links). Additionally, can serve the functionality of acting as a filter for these elements.
*/
class Legend extends Component {
  /**
   * Constructs React.Component with arguments `props` and `context`
   * @param {Object} props - React component properties
   * @param {Boolean} props.render -
   * @param {Object} props.graph - Object containing elements of the graph
   * @param {Object[]} props.graph.nodes - Array of Node objects (containing relevant information such as types and color)
   * @param {Object[]} props.graph.links - Array of Link objects (containing relevant information such as type and color)
   * @param {Object} context - ?? (I included it for consistency but have no idea what it is and could not figure it out)
   */
  constructor(props, context) {
    super(props, context);

    this.state = {
    };

  }

  /**
   * Formats the data in the graph by grouping all types
   * @private
   * @return {Object[]} - Formatted data
   */
  _getData(graph) {
    let nodes = graph.nodes;
    let links = graph.links;

    let nodeData = {};
    let linkData = {};
    /*
    Structure:
      {
      type: {
          elements: [...],
          color:"..."
        }
      }
    */
    nodes.forEach(node => {
      node.type.forEach(type => {
        if (type in nodeData) {
          nodeData[type].elements.push(node);
        }
        else {
          nodeData[type] = {
            callback:this.props.callback,
            elements:[node]
          }
        }
      });
    });
    links.forEach(link => {
      let type = link.type;
      if (type in linkData) {
        linkData[type].elements.push(link);
      }
      else {
        linkData[type] = {
          callback:this.props.callback,
          elements:[link]
        }
      }
    });
    return [
      {
        name: "Nodes",
        dataSet:nodeData
      },
      {
        name:"Links",
        dataSet:linkData
      }
    ];
  }

  /*
  TODO:
    (very high) if you press the run button a second time before it loads the first graph it crashes the site when the legend exists
    (high) decrease size

    (medium) make it so that it actually acts as a filter
      (low) => similar to reference legend, maybe add an option for each element type (node, link) to hide all (text would be something like '*' and the total amount of that element overall)

    (low) add visibility toggle widget
    (low) check if it needs optimization - if so, optimize
    (low) fully document
    (low) fix how it reacts when one container is empty
    (very low) possibly sort the colors somehow
  */

  render() {

    //Move some of this logic elsewhere? Not really supposed to have any in render, but I don't know where to properly place it
    // + Perhaps add callback in App.js when graph is set to update this graph property

    let graph = this.props.graph;
    console.log(graph);
    let data = this._getData(graph);

    // Better method?
    let length = 0;
    data.forEach(info => length += Object.keys(info.dataSet).length);


    // <ToggleButtonGroup type="checkbox" defaultValue={[...Array(Object.keys(elementData).length+1).keys()]}>
    //   {
    //     Object.keys(elementData).map((elementType,n) => {
    //       let color = elementData[elementType].color;
    //       // How to generate unique id??
    //       return <TypeButton value={n} data={{type: elementType, elements: elementData[elementType]}} key={n} />
    //     })
    //   }
    // </ToggleButtonGroup>


    if (this.props.render && length > 0) {
      return (
        <>
          <div id={this.props.id} className="Legend">
            {
              data.map((elementInfo,i) => {
                let elementData = elementInfo.dataSet;
                return (
                  // How to generate unique id??
                  <div className="graph-element-type-container" key={i}>
                  <h5 className="graph-element-header">{elementInfo.name}</h5>
                  <ButtonToolbar className="graph-element-content">
                    <TypeButtonGroup elementData={elementData} />
                  </ButtonToolbar>
                  </div>
                )
              })
            }
          </div>
        </>
      );
    }
    else {
      return null;
    }
  }
}

export default Legend;
