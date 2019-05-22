import React, { Component } from 'react';
import ReactTooltip from 'react-tooltip'
import { IoIosArrowDropupCircle, IoIosArrowDropdownCircle } from 'react-icons/io';
import { ButtonToolbar, ToggleButtonGroup, ToggleButton } from 'react-bootstrap';
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

    var RR = ((R.toString(16).length===1)?"0"+R.toString(16):R.toString(16));
    var GG = ((G.toString(16).length===1)?"0"+G.toString(16):G.toString(16));
    var BB = ((B.toString(16).length===1)?"0"+B.toString(16):B.toString(16));

    return "#"+RR+GG+BB;
}

// Legend button group component (TypeButton wrapper)
class TypeButtonGroup extends React.Component {
  constructor(props,context) {
    super(props,context);

    this._handleChange = this._handleChange.bind(this);

    this.state = {
      value:[]
    }
  }

  /**
   * Callback invoked when TypeButton child is pressed. Handles its `checked` property and calls its respective callback.
   *
   * @param {Array} value - Current value of ToggleButtonGroup (used to detect if the item should be added or removed).
   */
  _handleChange(value) {
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
    typeof this.props.callback === "function" && this.props.callback(newValue.type,turnedOn); //call the callback and pass on/off to it
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
          this.props.types.map((typeData,n) => {
            // How to generate unique id??
            if (typeData.color === null || typeData.color === undefined) return null;
            let checked = !(this.state.value.some(val => val.id === n));
            let data = {
              type: typeData.type,
              quantity: typeData.quantity,
              color: typeData.color
            };
            return <TypeButton value={Object.assign({id:n},data)} active={checked} data={data} key={n} />
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
      quantity:this.props.data.quantity,
      color:this.props.data.color,
      type: TypeButton.adjustTitle(this.props.data.type)
    };
  }

  /**
   * Adjust the title from camel case to title format (e.g "camel_case" => "Camel Case")
   *
   * @param {string} title - The string to be converted to title format
   *
   * @returns {string} - The string in title format
   */
  static adjustTitle(title) {
    // NOTE: This method of splitting by underscore will lead to adverse effects if types can have natural underscores in them
    // (Can they?)
    let newTitle = title.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    return newTitle;
  }

  render() {
    //Bootstrap doesn't like custom coloring schemes, but it is necessary here to deviate from the bootstrap color theme as it is specifically color-coded.
    //When a react-bootstrap ToggleButton is active, it uses the box-shadow property as what looks like the "border." This is set as the css variable `--highlight-box-shadow-color`,
    //so that it is only applied when active.
    let style = {
      backgroundColor:this.state.color,
      '--highlight-box-shadow-color':"rgb(50,50,50)"
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
        {this.state.type} <b>({this.state.quantity})</b>
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
   * @param {Boolean} props.render - If false, component will return null in `render` method
   * @param {Object} props.typeMappings - Type mappings of each graph element type (nodes/links)
   * @param {Object[]} props.nodes - Mappings of `type => number of nodes of type`
   * @param {Object[]} props.links - Mappings of `type => number of link of type`
   * @param {int} props.nodeTypeRenderAmount - Amount of node types rendered on the legend
   * @param {int} props.linkTypeRenderAmount - Amount of link types rendered on the legend
   *
   */
  constructor(props) {
    super(props);

    this.state = {
      collapse : false
    };

  }

  /**
   * Takes input mapping object and converts it to an array of zips sorted by their quantities
   *
   * @param {Object} typeMappings - Mappings of types of nodes and links to their quantities and colors
   * @param {Object} typeMappings.nodes - Node object mappings with structure `type` => {`color`,`quantity`}
   * @param {Object} typeMappings.links - Link object mappings with structure `type` => {`color`,`quantity`}
   *
   * @returns {Object} - New sorted mapping object with zipped structure
   *   {`nodes` : [{"type":`type`,"color":`color`,"quantity":`quantity`},...], `links` : [{"type":`type`,"color":`color`,"quantity",`quantity`},...]}
   * @private
   */
  _sortMappings(typeMappings) {
    let newMappings = {};
    // (object properties in javascript are unordered and therefore cannot be effectively)
    for (let graphElementType in typeMappings) {
      let sortedTypes = Object.entries(typeMappings[graphElementType]).sort((a,b) => b[1].quantity-a[1].quantity);
      let min = Math.min(graphElementType === "nodes" ? this.props.nodeTypeRenderAmount : this.props.linkTypeRenderAmount, sortedTypes.length);
      for (let i=0;i<min;i++) {
        if (!newMappings.hasOwnProperty(graphElementType)) newMappings[graphElementType] = [];
        newMappings[graphElementType].push(Object.assign({type:sortedTypes[i][0]},sortedTypes[i][1]));
      }
    }

    /*
    Structure:
      {
        "nodes": [
          {
            type:`type`,
            color:`color`,
            quantity:`quantity`
          },
          ...
        ],
        "links": [
          {
            type:`type`,
            color:`color`,
            quantity:`quantity`
          },
          ...
        ]
      }
    */
    return newMappings;
  }

  /*
  TODO:

    (medium) ask about nodes having multiple types and if they should hide if any types are filtered or if all are filtered

    (medium-low) maybe adjust it so that it shows the amount of nodes/links currently appearing or something similar to (n out of y nodes)

  */

  render() {
    //Move some of this logic elsewhere? Not really supposed to have any in render, but I don't know where to properly place it

    let typeMappings = this.props.typeMappings;

    let sortedMappings = this._sortMappings(typeMappings);


    let render = this.props.render;

    if (Object.keys(sortedMappings).length === 0) {
      // 0 elements in both nodes and links
      render = false;
    }
    if (this.state.collapse) {
      return (
          <div id={this.props.id} className="Legend">
            <IoIosArrowDropdownCircle data-tip="Open legend"
                                      className="legend-vis-control"
                                      onClick={(e) => this.setState({ collapse : false })}
                                      color="rgba(255,255,255,.5)"
            />
          </div>
      )
    }
    else if (render && sortedMappings.nodes.length + sortedMappings.links.length > 0) {
      // // If implemented, type property should be changed to something such as [type,Enum TypeFlag]
      // // So that there is no possibility to run into naming conflicts
      // Object.values(sortedMappings).forEach(elementType => {
      //   let total = elementType.reduce((acc,val) => acc + val.quantity, 0);
      //   elementType.push({
      //     color:"#a6aab5",
      //     type:"*",
      //     quantity:total
      //   });
      // });
      return (
        <div id={this.props.id} className="Legend">
          <ReactTooltip place="left"/>
          {/*+2px in margin-top is because of 2px border*/}
          <IoIosArrowDropupCircle onClick={(e) => this.setState({ collapse : true })} data-tip="Close legend" className="legend-vis-control"/>
          {
            Object.keys(typeMappings).map((elementType,i) => {
              let types = sortedMappings[elementType];
              return (
                // How to generate unique id??
                <div className="graph-element-type-container" key={i}>
                  <h6 className="graph-element-header">{elementType.charAt(0).toUpperCase()+elementType.slice(1)}</h6>
                  <ButtonToolbar className="graph-element-content">
                    <TypeButtonGroup callback={this.props.callback} types={types} />
                  </ButtonToolbar>
                </div>
              )
            })
          }
        </div>
      );
    }
    else {
      return null;
    }
  }
}

export default Legend;
