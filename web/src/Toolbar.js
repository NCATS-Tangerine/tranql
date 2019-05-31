import React, { Component } from 'react';
import ReactTooltip from 'react-tooltip';
import './Toolbar.css'

/**
 * Component allowing for the easy multifunctionality of a single tool slot (name is fairly misleading)
 *    Acts as a singular tool, which then can open a dropdown when held down which allows the user to replace the active tool with others contained within the ToolGroup
 *    As a visual explanation: The marquee group in Adobe Photoshop, which contains multiple different types of marquee tools (the default being the rectangular marquee).
 *    (Ex: https://i.gyazo.com/0bd4d63abd26eb8538e38836bb6be22e.png)
 */
export class ToolGroup extends Component {
  /**
   * Constructs a new ToolGroup component
   *
   * @param {Object} props - Properties of the ToolGroup
   * @param {Tool[]} props.children - Tools that are contained within the ToolGroup.
   * @param {int} [props.default=0] - Index in props.children of the default selected tool
   */
   constructor(props) {
     super(props);

     this._selectActive = this._selectActive.bind(this);
     this._leave = this._leave.bind(this);
     this._showSelectMenu = this._showSelectMenu.bind(this);
     this.setActive = this.setActive.bind(this);

     // For some reason children isn't an array when there is only one child
     let children = (!Array.isArray(this.props.children)) ? [this.props.children] : this.props.children;

     if (children.length === 0) throw new Error("ToolGroup must contain at minimum one Tool");
     children = children.map((comp, index) => {
       // There is a better way to do this in React 0.14+, but I could not get it to work.
       if (comp.type !== Tool) {
         throw new Error("ToolGroup must only contain components of type Tool, not type '"+(typeof comp.type === 'string' ? comp.type : comp.type.name)+"'");
       }
       return React.cloneElement(comp, {
         onMouseDown: (e) => {
           e.preventDefault();
           this._selectActive(index);
         },
         onMouseUp: (e) => {
           this._leave(index);
         },
         toolbarCallback:this.props.toolbarCallback,
         key:index,
         ref:React.createRef(),
         tipProp: comp.props.name+" - "+comp.props.description,
         name: undefined, // Gets in the way when menu is open so we'll conditionally render it on the container, rather than the tool
       });
     });

     this.state = {
       selectMenuHover: false,
       selectMenu: null,
       children: children,
       activeTool: this.props.hasOwnProperty('default') ? this.props.default : 0
     };
   }

   /* ToolGroup class needs to be able to function as if it were an instance of a Tool */
   setActive(active) {
     /* If none are currently active and the toolbar requests to set ToolGroup to active, set the currently active Tool */
     if (active && this.state.children.every(tool => !tool.ref.current.state.active)) {
        this._activeTool.ref.current.setActive(active);
     }
     else {
       this.state.children.forEach((tool,i) => {
         tool.ref.current.state.active && tool.ref.current.setActive(active);
       });
     }
   }

   get _activeTool() {
     return this.state.children[this.state.activeTool];
   }

   set _activeTool(index) {
     this.setState(prevState => {
       return {activeTool:index};
     }, () => {
       this.state.children.forEach((tool,i) => {
         tool.ref.current.setActive(i === index);
       });
     });
   }

   _showSelectMenu() {
     const leaveCallback = () => {
       this.setState(prevState => {
         return {
           selectMenuHover: false,
           selectMenu: null
         };
       });
     }
     let selectMenu = (
       <div onMouseLeave={leaveCallback}
            onMouseEnter={this.setState({selectMenuHover:true})}
            className="select-menu"
       >
        {
          this.state.children.map((tool,index) => {
            return (
              <div key={index} className="select-menu-tool" data-active-tool={this.state.activeTool === index} onClick={() => this._selectActive(index,true)}>
                {/* Clone the icon of the tool (children is a component when only one child exists) */}
                {React.cloneElement(tool.props.children)} {tool.props.description}
              </div>
            );
          })
        }
       </div>
     );
     this.setState({ selectMenu : selectMenu });
   }

   _leave(index) {
     if (this.state.selectMenu) {
       if (!this.state.selectMenuHover) {
         this.setState({
           selectMenuHover: false,
           selectMenu: null
         });
       }
     }
     else {
       clearInterval(this.state.children[index].ref.current.holdTimeout);
       this._activeTool = index;
     }
   }

   _selectActive(index,selectMenu=false) {
     let tool = this.state.children[index];
     let active = this._activeTool === tool;
     if (selectMenu) {
       this._activeTool = index;
       this.setState({ selectMenu: null, selectMenuHover: false});
     }
     else if (active) {
       tool.ref.current.holdTimeout = setTimeout(() => {
         this._showSelectMenu();
       },500);
     }
   }

   render() {
     return (
        <div className="tool-group" style={{position:"relative"}} data-html={true} data-tip={this.state.selectMenu === null ? this._activeTool.props.tipProp : undefined}>
          {/* ^data-tip does not render if select menu is open */}
          {this._activeTool}
          {this.state.selectMenu}
          {/* This is really bad but they lose their refs when they're not rendered */}
          <div style={{display:"none"}}>{this.state.children.map(tool => tool !== this._activeTool && tool)}</div>
        </div>
     );
   }
}

/**
 * @callback onClick
 * @param {Object} clickEvent - The click event that is fired
 */

/**
 * Component used to define, represent, and act as a tool in a Toolbar or ToolGroup component.
 *
 */
export class Tool extends Component {
  /**
   * Constructs a new Tool component
   *
   * @param {Object} props - Properties of the Tool
   * @param {string} props.name - Name of the tool
   * @param {string} props.description - Description of the tool (keep it short). Only functional when contained in a ToolGroup.
   * @param {onClick} props.callback - Callback invoked on click
   * @param {Component} props.children - Icon of the child (e.g. <IoIosSettings />)
   */
  constructor(props) {
    super(props);

    if (this.props.children === undefined) throw new Error("Tool must contain icon component");
    if (Array.isArray(this.props.children)) throw new Error("Tool must contain icon component as the only child");

    this.state = {
      active: false
    };

    // this.setActive = this.setActive.bind(this);
  }

  setActive(act) {
    this.setState(prevState => {
      if (act !== prevState.active) {
        this.props.callback(act);
        if (act) {
          this.props.toolbarCallback(this);
        }
      }
      return { active: act };
    });
  }

  render() {
    return (
      <div className="Tool"
           onMouseUp={this.props.onMouseUp || (() => {this.setActive(true);})}
           onMouseDown={this.props.onMouseDown}
           data-tip={this.props.name !== undefined && this.props.description !== undefined ? this.props.name+" - "+this.props.description : undefined}
           data-html={true}
           data-active-tool={this.state.active}>
        {
          /* this.props.children is a single component (not an array) when only one child is present */
          this.props.children
        }
      </div>
    );
  }
}

/**
 * Toolbar component that contains ToolGroup and Tool components.
 *
Ex:
const tools = (
  <ToolGroup default={1}>
    <Tool name="Select" description="Select a node or link" callback={(e) => console.log("foobar",e)}>
      <FaMousePointer/>
    </Tool>
    <Tool name="Testing" description="Testing tool" callback={(e) => console.log("test",e)}>
      <FaBan/>
    </Tool>
  </ToolGroup>,
  <Tool name="NavigateTest" description="Navigate along the graph" callback={(e) => console.log("other",e)}>
    <FaArrowsAlt/>
  </Tool>
);
<Toolbar default={1} tools={tools}/>
*/
export class Toolbar extends Component {
  /**
   * Constructs a new Toolbar component
   *
   * @param {Object} props - Properties of toolbar
   * @param {Tool[]} props.tools - Array of tool groups and tools contained within the toolbar.
   *    NOTE: Tools are not required to be contained inside of ToolGroups, the name may be misleading. Make sure to check out what a ToolGroup actually does.
   * @param {Component[]} props.buttons - Array of components (icons) contained at the bottom of the toolbar.
   *    The Toolbar does not modify these components in any way. It simply provides a container for them to be better placed within the larger document.
   * @param {int} [props.default=0] - Index in props.tools of the default active tool (its callback will be invoked to select it)
   */
  constructor(props) {
    super(props);

    this._setActiveTool = this._setActiveTool.bind(this);

    this.state = {
      tools: this.props.tools.map((tool,i) => {
        return React.cloneElement(tool, {
          toolbarCallback: this._setActiveTool,
          ref:React.createRef()
        });
      }),
    };

  }

  _setActiveTool(tool) {
    this.state.tools.forEach((tool2,i) => {
      tool !== tool2.ref.current && tool2.ref.current.setActive(false);
    });
  }

  componentDidMount() {
    let defaultTool = this.props.hasOwnProperty('default') ? this.state.tools[this.props.default].ref.current : this.state.tools[0].ref.current;
    defaultTool.setActive(true);
    this._setActiveTool(defaultTool);
  }

  render() {
    return (
      <div id={this.props.id} className="Toolbar">
        <ReactTooltip place="left"/>
        <div className="toolbar-header"></div>
        <div className="toolbar-content toolbar-button-container">
        {
          this.props.buttons.map((button,i) => {
            return (
              <div key={i} className='tool-container'>
              {button}
              </div>
            )
          })
        }
        </div>
        <div className="toolbar-content">
          {
            this.state.tools.map((tool,i) => {
              return (
                <div key={i} className='tool-container'>
                  {tool}
                </div>
              )
            })
          }
        </div>
      </div>
    )
  }

}
