import React, { Component } from 'react';
import ReactTooltip from 'react-tooltip'
import { IoIosArrowDropupCircle, IoIosArrowDropdownCircle } from 'react-icons/io';
import { ButtonToolbar, ToggleButtonGroup, ToggleButton } from 'react-bootstrap';
import { shadeColor, hydrateState } from './Util.js';
import './Legend.css';

// Legend button group component (TypeButton wrapper)
class TypeButtonGroup extends React.Component {
  /**
   * @param {string[]} props.hiddenTypes - Either hiddenTypes.nodes or hiddenTypes.links
   */
  constructor(props,context) {
    super(props,context);

    this._handleChange = this._handleChange.bind(this);
  }

  /**
   * Callback invoked when TypeButton child is pressed. Handles its `checked` property and calls its respective callback.
   *
   * @param {Array} value - Current value of ToggleButtonGroup (used to detect if the item should be added or removed).
   */
  _handleChange(value) {
    let newValue = value[value.length-1];
    let newState = this.props.hiddenTypes.slice();
    let turnedOn = false;
    this.props.hiddenTypes.forEach((value,i) => {
      let type = value;
      if (type === newValue.type) {
        newState.splice(i,1);
      }
    });
    if (newState.length === this.props.hiddenTypes.length) {
      newState.push(newValue.type);
      turnedOn = true;
    }
    typeof this.props.callback === "function" && this.props.callback(this.props.graphElementType,newValue.type,turnedOn); //call the callback and pass on/off to it
    // this.setState({ value: newState });
  }

  render() {
    return (
      <ToggleButtonGroup
        type="checkbox"
        value={this.props.hiddenTypes}
        onChange={this._handleChange}
      >
        {
          this.props.types.map((typeData,n) => {
            // How to generate unique id??
            let checked = this.props.hiddenTypes.every(val => val !== typeData.type);
            let data = {
              type: typeData.type,
              quantity: typeData.quantity,
              actualQuantity: typeData.hasOwnProperty('actualQuantity') ? typeData.actualQuantity : 0,
              color: typeData.color
            };
            return <TypeButton onContextMenu={this.props.onContextMenu} value={data} active={checked} data={data} key={n} />
          })
        }
      </ToggleButtonGroup>
    );
  }
}

// Legend button component
class TypeButton extends Component {
  render() {
    //Bootstrap doesn't like custom coloring schemes, but it is necessary here to deviate from the bootstrap color theme as it is specifically color-coded.
    //When a react-bootstrap ToggleButton is active, it uses the box-shadow property as what looks like the "border." This is set as the css variable `--highlight-box-shadow-color`,
    //so that it is only applied when active.
    let style = {
      backgroundColor:this.props.data.color,
      '--highlight-box-shadow-color':'rgb(50,50,50)',
      '--hover-background-color':shadeColor(this.props.data.color,-10)
    };
    //Set var '--highlight-color' in inline style property to be accessed when focused

    //Better way of extending react component and passing on properties?
    return (
      <ToggleButton
        style={style}
        name={this.props.name}
        type={this.props.type}
        onChange={this.props.onChange}
        onContextMenu={(e) => typeof this.props.onContextMenu === "function" && this.props.onContextMenu(e, this.props.active,this.props.data.type)}
        checked={this.props.active}
        value={this.props.value}
        size="sm"
        className="TypeButton">
        {this.props.active ? <b>{(this.props.data.type)}</b> : (this.props.data.type)}
        {this.props.active ? <b>({this.props.data.actualQuantity}/{this.props.data.quantity})</b> : "("+this.props.data.actualQuantity+"/"+this.props.data.quantity+")"}
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
   *
   * @param {Object} props - React component properties
   * @param {Boolean} props.render - If false, component will return null in `render` method
   * @param {Object} props.typeMappings - Type mappings of each graph element type (nodes/links)
   * @param {Object[]} props.typeMappings.nodes - Mappings of `type => number of nodes of type` (e.g. {"chemical_substance":800})
   * @param {Object[]} props.typeMappings.links - Mappings of `type => number of link of type`
   * @param {int} props.nodeTypeRenderAmount - Amount of node types rendered on the legend
   * @param {int} props.linkTypeRenderAmount - Amount of link types rendered on the legend
   * @param {Function} props.callback - Invoked when a button is left clicked.
   * @param {Function} [props.onContextMenu=undefined] - Invoked when a context menu is opened on a button (right click).
   *    Passes the arguments:
   *      {MouseEvent} event - The mouse event emited when the contextmenu event is fired (can be prevented),
   *      {Boolean} active - If the button is active or not.
   *      {String} type - The type that the button represents.
   *
   */
  constructor(props) {
    super(props);

    this.state = {
      collapse : false
    };

    this._hydrateState = hydrateState.bind(this);
  }

  /**
   * Takes input mapping object and converts it to an array of zips sorted by their quantities
   *
   * @param {Object} typeMappings - Mappings of types of nodes and links to their quantities and colors
   * @param {Object} typeMappings.nodes - Node object mappings with structure `type` => {`color`,`quantity`}
   * @param {Object} typeMappings.links - Link object mappings with structure `type` => {`color`,`quantity`}
   * @param {String[]} hiddenTypes - Array of strings specifying the hidden types contained within the typeMappings.
   *    This allows the Legend to make each type button the correct state (on/off) when rendering.
   * @static
   * @returns {Object} - New sorted mapping object with zipped structure
   *    {'nodes' : [{"type":`type`,"color":`color`,"quantity":`quantity`},...], 'links' : [{"type":`type`,"color":`color`,"quantity",`quantity`},...]}
   */
  static sortMappings(typeMappings, nodeTypeRenderAmount, linkTypeRenderAmount) {
    let newMappings = {
      nodes: [],
      links: []
    };
    // (object properties in javascript are unordered and therefore cannot be effectively)
    for (let graphElementType in typeMappings) {
      let sortedTypes = Object.entries(typeMappings[graphElementType]).sort((a,b) => b[1].quantity-a[1].quantity);
      let min = Math.min(graphElementType === "nodes" ? nodeTypeRenderAmount : linkTypeRenderAmount, sortedTypes.length);
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

  componentDidMount() {
    this._hydrateState();
  }

  render() {
    //Move some of this logic elsewhere? Not really supposed to have any in render, but I don't know where to properly place it

    let typeMappings = this.props.typeMappings;

    let sortedMappings = Legend.sortMappings(typeMappings, this.props.nodeTypeRenderAmount, this.props.linkTypeRenderAmount);


    let render = this.props.render;
    if (Object.keys(sortedMappings.nodes).length + Object.keys(sortedMappings.links).length === 0) {
      // 0 elements in both nodes and links
      //
      // Commented as it can be confusing that the legend is gone. Instead displays text that indicates its emptiness
      // render = false;
    }
    if (render) {
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
      if (this.state.collapse) {
        return (
          <div id={this.props.id} className="Legend" data-closed={true}>
          {/*<h6 className="legendHeader">Legend</h6>*/}
          <ReactTooltip place="left"/>
          <IoIosArrowDropdownCircle data-tip="Open legend"
          className="legend-vis-control-open"
          onClick={(e) => {
            this.setState({ collapse : false })
            localStorage.setItem('collapse', false);
          }}
          color="rgba(40,40,40,1)"
          />
          </div>
        );
      }
      else {
        return (
          <div id={this.props.id} className="Legend">
          {/*+2px in margin-top is because of 2px border*/}
          <IoIosArrowDropupCircle onClick={(e) => {
            this.setState({ collapse : true });
            localStorage.setItem('collapse', true);
          }} data-tip="Close legend" className="legend-vis-control"/>
          {
            Object.keys(sortedMappings).map((elementType,i) => {
              let types = sortedMappings[elementType];
              return (
                // How to generate unique id??
                <div className="graph-element-type-container" key={i}>
                <h6 className="graph-element-header">
                  {
                    // If the legend has no types to display for said elementType, make clear that it is empty
                    // Else, render how many currently aren't being displayed. If all are being display, do nothing.
                    elementType.charAt(0).toUpperCase()+elementType.slice(1) + (types.length === 0 ?
                      ' (empty)' :
                      Object.keys(typeMappings[elementType]).length-types.length ?
                        ` (and ${Object.keys(typeMappings[elementType]).length-types.length} more)` :
                        '')
                  }
                </h6>
                <ButtonToolbar className="graph-element-content">
                <TypeButtonGroup hiddenTypes={this.props.hiddenTypes[elementType]} graphElementType={elementType} callback={this.props.callback} types={types} onContextMenu={this.props.onContextMenu}/>
                </ButtonToolbar>
                </div>
              )
            })
          }
          </div>
        );
      }
    }
    else {
      return null;
    }
  }
}

export default Legend;
