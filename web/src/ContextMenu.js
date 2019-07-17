import React, { Component } from 'react';
import { Menu, Item, Separator } from 'react-contexify';
import 'react-contexify/dist/ReactContexify.min.css';

class ContextMenu extends Component {
  constructor(props) {
    /* Create state elements and initialize configuration. */
    super(props);
    this._handleClick = this._handleClick.bind (this);
    this._menu = React.createRef ();
  }
  _handleClick = (e) => {
    console.log(e);
  }
  render () {
    /*
          <Separator />
          <Submenu label="Foobar">
            <Item onClick={this._handleClick}>Foo</Item>
            <Item onClick={this._handleClick}>Bar</Item>
          </Submenu>
     */
    return (
        <Menu id={this.props.id}>
          <Item>This menu is TBD</Item>
          <Separator />
          <Item>Node similarity</Item>
          <Separator />
          <Item>Browse Neighbors</Item>
          <Separator />
          <Item>Compare to Last Answer</Item>
        </Menu>
    );
  }
}
export default ContextMenu;
