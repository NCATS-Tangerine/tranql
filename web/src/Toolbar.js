import React, { Component } from 'react';
import ReactTooltip from 'react-tooltip';
import { CSSStringtoRGB } from './Util.js';
import './Toolbar.css';

class SelectMenu extends Component {
  constructor(props) {
    super(props);
    this.state = {
      selectMenuHover: false,
      active: false
    }
  }
  setActive() {
    this.setState({ active : true });
    Toolbar._resize();
  }
  render() {
    if (!this.state.active) return null;
    return (
      <div onMouseLeave={this.props.leaveCallback}
           onMouseEnter={() => this.setState({selectMenuHover:true})}
           className="select-menu"
      >
       {
         this.props.children.map((tool,index) => {
           return (
             <div key={index} className="select-menu-tool" data-active-tool={this.props.activeTool === index} onClick={() => this.props.onClick(index)}>
               {/* Clone the icon of the tool (children is a component when only one child exists) */}
               {React.cloneElement(tool.props.children)} {tool.props.description}
             </div>
           );
         })
       }
      </div>
    );
  }
}

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
         ...comp.props,
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
         onlyUseShortcutsWhen: this.props.onlyUseShortcutsWhen,
         tipProp:Tool.makeTip(comp.name,comp.description,comp.shortcut),
         // Hide the tooltip
         name:undefined
       });
     });

     this.state = {
       children: children,
       activeTool: this.props.hasOwnProperty('default') ? this.props.default : 0
     };

     this._selectMenu = React.createRef();
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
     this._selectMenu.current.setActive();
     // let selectMenu = ;
     // this.setState({ selectMenu : selectMenu });
   }

   _leave(index) {
     if (this._selectMenu.current.active) {
       if (!this._selectMenu.current.state.selectMenuHover) {
         this._selectMenu.current.setState({ active : false });
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
       this._selectMenu.current.setState({ active : false });
     }
     else if (active) {
       tool.ref.current.holdTimeout = setTimeout(() => {
         this._showSelectMenu();
       },500);
     }
   }

   render() {
     return (
        <div className="tool-group" style={{position:"relative"}}>
          {this._activeTool}
          <SelectMenu leaveCallback={() => this._selectMenu.current.setState({ active : false })}
                                       children={this.state.children}
                                       activeTool={this.state.activeTool}
                                       ref={this._selectMenu}
                                       onClick={(index) => this._selectActive(index,true)}/>
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
   * @param {String} props.name - Name of the tool
   * @param {String} props.description - Description of the tool (keep it short). Only functional when contained in a ToolGroup.
   * @param {Component} props.children - Icon of the child (e.g. <IoIosSettings />).
   * @param {Function} [props.callback=function(){}] - Callback invoked on click.
   * @param {Number|String|Array<Number|String>} props.shortcut - Keycode or key for the shortcut. When a string, it is case sensitive.
   *    If an array, the shortcut will trigger if any of the keys/key codes contained are pressed.
   *    Array may be of mixed types.
   */
  constructor(props) {
    super(props);

    if (this.props.children === undefined) throw new Error("Tool must contain icon component");
    if (Array.isArray(this.props.children) && this.props.children.length > 1) throw new Error("Tool must contain icon component as the only child");

    this.state = {
      addedCursor: false,
      active: false,
      shortcut: Array.isArray(this.props.shortcut) ? this.props.shortcut : [this.props.shortcut]
    };

    this._DOMNode = React.createRef();

    this.setActive = this.setActive.bind(this);
    this.cursorify = this.cursorify.bind(this);
    this.addCursor = this.addCursor.bind(this);
    this.revokeCursor = this.revokeCursor.bind(this);
    this.setCursor = this.setCursor.bind(this);

    this._keyDownCallback = this._keyDownCallback.bind(this);
    // this.setActive = this.setActive.bind(this);
  }
  /**
   * Convert the child icon to an base64-encoded png that can be used as a cursor
   *
   * @returns {String} - The data URL of the image
   */
  cursorify() {
    try {
      return new Promise((resolve,reject) => {
        const canvas = document.createElement('canvas');
        const svgElement = this._DOMNode.current.children[0].cloneNode(true);
        const size = 28;
        svgElement.setAttribute('width',size+'px');
        svgElement.setAttribute('height',size+'px');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        const svgString = new XMLSerializer().serializeToString(svgElement);
        const image = new Image();
        const svg = new Blob([svgString],{type:'image/svg+xml;charset=utf-8'});
        const url = URL.createObjectURL(svg);
        // const color = CSSStringtoRGB(window.getComputedStyle(this._DOMNode.current.children[0]).color);
        let color = {
          r:255,
          g:255,
          b:255,
          a:1
        };
        image.onload = function() {
          ctx.drawImage(image,0,0);
          let data = ctx.getImageData(0,0,size,size);
          for (let i=0;i<data.data.length;i+=4) {
            let r = data.data[i];
            let g = data.data[i+1];
            let b = data.data[i+2];
            let a = data.data[i+3];
            if (r !== 0 || g !== 0 || b !== 0 || a !== 0) {
              data.data[i] = color.r;
              data.data[i+1] = color.g;
              data.data[i+2] = color.b;
              data.data[i+3] = color.a * 255;
            }
          }
          ctx.putImageData(data,0,0);
          resolve(`url(${canvas.toDataURL('image/png')}), auto`);
        }
        image.src = url;
      });
    }
    catch (e) {
      // Probably not an element that can be drawn via `drawImage`
      console.warn(e);
    }
  }
  addCursor() {
    this._cursorIcon.then((url) => {
      if (this.state.addedCursor) {
        return;
      }
      this.setState(({ addedCursor : true }));
      // console.log('set',this.props.name);
      document.querySelector('body').style.cursor = url;
      document.querySelector('body').setAttribute('data-cursor-url',url);
    });
  }
  revokeCursor() {
    this._cursorIcon.then((url) => {
      if (!this.state.addedCursor) {
        return;
      }
      this.setState(({ addedCursor : false }));
      if (document.querySelector('body').getAttribute('data-cursor-url') === url) {
        // console.log('revoke',this.props.name);
        document.querySelector('body').style.cursor = `auto`;
      }
    });
  }
  setCursor() {
    typeof this._cursorIcon !== "undefined" && (this.props.overrideCursor && this.state.active ? this.addCursor() : this.revokeCursor());
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

  _keyDownCallback(e) {
    if (this.props.onlyUseShortcutsWhen.some(type => document.activeElement instanceof type)) {
      let char = String.fromCharCode(e.keyCode);
      if (e.ctrlKey) {
        return;
      }
      if (!e.shiftKey) {
        char = char.toLowerCase();
      }
      if (typeof this.props.shortcut !== "undefined" && (this.state.shortcut.includes(e.keyCode) || this.state.shortcut.includes(char))) {
        this.props.onMouseUp ? this.props.onMouseUp() : this.setActive(true);
      }
    }
  }

  static makeTip(name,description,shortcut) {
    return (name !== undefined && description !== undefined ? (
      name +
      " - "+description +
      (typeof shortcut !== "undefined" ?
        (" ("+(Array.isArray(shortcut) ?
          shortcut :
          [shortcut]).map(key=>(typeof key==="string" ?
            (key === key.toUpperCase() ?
              "shift+" + key :
              key.toUpperCase()) :
            String.fromCharCode(key)
          ))
          .join("/")+")") :
        ""
        )
    ) : undefined);
  }

  componentWillUnmount() {
    document.removeEventListener('keydown', this._keyDownCallback);
  }

  componentDidMount() {
    document.addEventListener('keydown', this._keyDownCallback);

    this._cursorIcon = this.cursorify();
  }


  render() {
    this.setCursor();
    return (
      <div className="Tool"
           ref={this._DOMNode}
           onMouseUp={this.props.onMouseUp || (() => {this.setActive(true);})}
           onMouseDown={this.props.onMouseDown}
           data-tip={Tool.makeTip(this.props.name,this.props.description,this.props.shortcut)}
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
  static defaultProps = {
    default: 0,
    overrideCursor: true,
    onlyUseShortcutsWhen: []
  };
  /**
   * Constructs a new Toolbar component
   *
   * @param {Object} props - Properties of toolbar
   * @param {Array<ToolGroup|Tool>} props.tools - Array of tool groups and tools contained within the toolbar.
   *    NOTE: Tools are not required to be contained inside of ToolGroups, the name may be misleading. Make sure to check out what a ToolGroup actually does.
   * @param {Component[]} props.buttons - Array of components (icons) contained at the bottom of the toolbar.
   *    The Toolbar does not modify these components in any way. It simply provides a container for them to be better placed within the larger document.
   * @param {int} [props.default=0] - Index in props.tools of the default active tool (its callback will be invoked to select it)
   * @param {Boolean} [props.overrideCursor=true] - Determines whether or not the tools will override the default page cursor when active.
   * @param {Array<HTMLElement|String>} [props.onlyUseShortcutsWhen=[]] - Shortcuts will only fire when the document's active element is of a type that inherits HTMLElement contained within this array or has the same id as a string in this array.
   */
  constructor(props) {
    super(props);

    this._setActiveTool = this._setActiveTool.bind(this);

    this.state = {
      tools: this.props.tools.map((tool,i) => {
        return React.cloneElement(tool, {
          toolbarCallback: this._setActiveTool,
          ref:tool.ref !== null ? tool.ref : React.createRef()
        });
      }),
    };
  }

  get activeTool() {
    return this.state.tools.filter((tool) => tool.ref.current.state.active)[0].ref.current;
  }

  _setActiveTool(tool) {
    this.state.tools.forEach((tool2,i) => {
      tool !== tool2.ref.current && tool2.ref.current.setActive(false);
    });
  }

  static _resize(e) {
    // Quite the hack but there doesn't seem to be any other alternative
    let menus = document.querySelectorAll('.select-menu');
    for (let i=0;i<menus.length;i++) {
      const menu = menus[i];
      menu.style.left = menu.parentElement.getBoundingClientRect().left + menu.parentElement.offsetWidth + "px";
      menu.style.top = menu.parentElement.getBoundingClientRect().top + "px";
    }
  }

  componentDidMount() {
    let defaultTool = this.props.hasOwnProperty('default') ? this.state.tools[this.props.default].ref.current : this.state.tools[0].ref.current;
    defaultTool.setActive(true);
    this._setActiveTool(defaultTool);
    window.addEventListener('resize',Toolbar._resize);
    document.addEventListener('scroll',Toolbar._resize);
  }

  componentWillUnmount() {
    window.removeEventListener('resize',Toolbar._resize);
    document.removeEventListener('scroll',Toolbar._resize);
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
                  {React.cloneElement(tool,{onlyUseShortcutsWhen: this.props.onlyUseShortcutsWhen, overrideCursor: this.props.overrideCursor, ...tool.props})}
                </div>
              )
            })
          }
        </div>
      </div>
    )
  }

}
