import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import { FaTimes, FaSpinner } from 'react-icons/fa';
import { Button } from 'reactstrap';
import { Typeahead } from 'react-bootstrap-typeahead';
import { toQueryString } from './Util.js';
import * as THREE from 'three';
import 'react-bootstrap-typeahead/css/Typeahead.css';
import './BrowseNodeInterface.css';

export default class BrowseNodeInterface extends Component {
  constructor(props) {
    super(props);

    this.state = {
      node : null,
      activeConcept : '',
      activePredicate : '',
      loading : false
    };

    this.hide = this.hide.bind(this);
    this.selectNode = this.selectNode.bind(this);
    this._browseNode = this._browseNode.bind(this);
    this._getPos = this._getPos.bind(this);
    this._updatePosition = this._updatePosition.bind(this);

    this._root = React.createRef ();

    this._controller = new window.AbortController();
  }
  hide() {
    if (this.state.loading) {
      this._controller.abort();
    }
    this.setState({ node : null, activeConcept : '', activePredicate : '', loading : false });

  }
  selectNode(node,e) {
    // Object.keys(node.__threeObj.position).forEach((key) => {
    //   (() => {
    //     let value = node.__threeObj.position[key];
    //     Object.defineProperty(node.__threeObj.position,key,{
    //       get: function() { return value; },
    //       set: (v) => {
    //         value = v;
    //         this._updatePosition();
    //       }
    //     });
    //   })();
    // });
    this.setState({ node : node }, () => {
      this._updatePosition();
    });
  }
  async _browseNode() {
    this.setState({ loading : true });
    const params = {};
    if (this.state.activePredicate !== '') params.predicate = this.state.activePredicate;
    let queryString = Object.keys(params).length === 0 ? '' : ('?'+toQueryString(params));

    let fetches = [];
    this.state.node.type.forEach((type) => {
      fetches.push(
        fetch(this.props.robokop_url+`/api/simple/expand/${type}/${this.state.node.id}/${this.state.activeConcept}/${queryString}`)
      )
    });

    await Promise.all(fetches);

    console.log(fetches);
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
        <div className="browse-node-header">
          <h6>Browse Node</h6>
          {this.state.loading ? (<FaSpinner className="fa-spin"/>) : null}
        </div>
        <div className="browse-node-body">
          <div>
            <span>Source id:</span>
            <div>
              <input type="text" disabled value={this.state.node.id} className="form-control"/>
            </div>
          </div>
          <div>
            <span>Target type:</span>
            <Typeahead multiple={false}
                       id='browseNodeConcept'
                       placeholder={'Enter a biolink modal concept type...'}
                       onChange={(concept)=>{
                        this.setState({ activeConcept : concept[0] });
                       }}
                       options={this.props.concepts}/>
          </div>
          <div>
            <span>Predicate (optional):</span>
            <Typeahead multiple={false}
                       id='browseNodePredicate'
                       placeholder={'Enter a biolink modal edge type...'}
                       onChange={(relation)=>{
                        this.setState({ activePredicate : relation[0] });
                       }}
                       options={this.props.relations}/>
          </div>
          <div className="button-container">
            <Button color="primary"
                    disabled={this.state.loading}
                    onClick={(e)=>this._browseNode()}>
              Execute
            </Button>

            <Button color="danger"
            onClick={(e)=>this.hide()}>
              Cancel
            </Button>
          </div>
        </div>
      </div>
    );
  }
}
