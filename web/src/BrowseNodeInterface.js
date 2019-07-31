import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import * as THREE from 'three';
import './BrowseNodeInterface.css';

export default class BrowseNodeInterface extends Component {
  constructor(props) {
    super(props);

    this.state = {
      node : null
    };

    this.hide = this.hide.bind(this);
    this.selectNode = this.selectNode.bind(this);
    this._browseNode = this._browseNode.bind(this);
    this._getPos = this._getPos.bind(this);
    this._updatePosition = this._updatePosition.bind(this);

    this._root = React.createRef ();
  }
  hide() {
    this.setState({ node : null });
  }
  selectNode(node) {
    Object.keys(node.__threeObj.position).forEach((key) => {
      (() => {
        let value = node.__threeObj.position[key];
        Object.defineProperty(node.__threeObj.position,key,{
          get: function() { return value; },
          set: (v) => {
            value = v;
            this._updatePosition();
          }
        });
      })();
    });
    this.setState({ node : node });
  }
  _browseNode() {

  }
  _updatePosition() {
    const pos = this._getPos();
    const node = ReactDOM.findDOMNode(this._root.current);
    node.style.left = pos.x + "px";
    node.style.top = pos.y + "px";
  }
  _getPos() {
    const node = this.state.node;
    const position = new THREE.Vector3(node.x,node.y,node.z);
    const vector = position.project(this.props.fg.camera())
    vector.x = (vector.x + 1) / 2 * this.props.fg.rootElem.offsetWidth;
    vector.y = -(vector.y - 1) / 2 * this.props.fg.rootElem.offsetHeight;
    return {
      x:vector.x,
      y:vector.y
    }
  }
  render() {
    if (this.state.node === null) return null;
    return (
      <div className="BrowseNodeInterface" ref={this._root}>
        <h6 className="horizontal-bar">{this.state.node.name}</h6>
      </div>
    );
  }
}
