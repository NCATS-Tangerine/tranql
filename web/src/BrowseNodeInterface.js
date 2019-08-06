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
    this._error = this._error.bind(this);

    this._root = React.createRef ();

    this._controller = new window.AbortController();

    this._REASONER = 'robokop';
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
  _error(errors) {
    if (!Array.isArray(errors)) errors = [errors];

    this.setState({ loading : false });
    this.props.onReturnError(errors);
  }
  async _browseNode() {
    this.setState({ loading : true });
    const params = {};
    if (this.state.activePredicate !== '') params.predicate = this.state.activePredicate;
    let queryString = Object.keys(params).length === 0 ? '' : ('?'+toQueryString(params));

    const fetches = [];
    const errors = [];

    for (let i=0;i<this.state.node.type.length;i++) {
      try {
        const type = this.state.node.type[i];
        this._controller = new window.AbortController();
        const resp = await fetch(this.props.robokop_url+`/api/simple/expand/${type}/${this.state.node.id}/${this.state.activeConcept}/${queryString}`, {
          signal: this._controller.signal
        });
        if (resp.ok) {
          const json = await resp.json();
          this._controller = new window.AbortController();
          const decorated_resp = await fetch(this.props.tranqlURL+'/tranql/decorate_kg',{
            signal: this._controller.signal,
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              'knowledge_graph' : json.knowledge_graph,
              'reasoner' : this._REASONER
            })
          });
          json.knowledge_graph = await decorated_resp.json();
          fetches.push(
            json
          );
        }
      }
      catch (e) {
        errors.push(e);
      }
      console.log('Finished request',(i+1).toString());
    }
    if (errors.length > 0) {
      this._error(errors);
      return;
    }
    console.log(fetches);

    console.log('Beginning merge request');
    try {
      this._controller = new window.AbortController();
      const resp = await fetch(this.props.tranqlURL+'/tranql/merge_messages',{
        signal: this._controller.signal,
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          'messages' : [
            this.props.message,
            ...fetches
          ],
          'interpreter_options' : {
            'name_based_merging' : true,
            'resolve_names' : false
          }
        })
      });
      const merged = await resp.json();
      console.log('Finished browse node');
      this.hide();
      this.props.onReturnResult(merged);
    }
    catch (e) {
      this._error(e);
    }
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
  _getValidProps(nodes,edges,isPredicate) {
    nodes = nodes.filter((item) => item.reasoner.includes(this._REASONER));
    edges = edges.filter((item) => item.reasoner.includes(this._REASONER));
    if (isPredicate) {
      const activeConcept = this.state.activeConcept;
      return edges.filter((edge) => {
        return (
          this.state.node.type.includes(edge.source_id) &&
          (activeConcept === '' || activeConcept === edge.target_id)
        );
      }).flatMap((edge) => edge.type);
    }
    else {
      const predicate = this.state.activePredicate;
      const validPredicates = nodes.filter((node) => {
        return edges.filter((edge) => {
          return (
            this.state.node.type.includes(edge.source_id) &&
            edge.target_id === node.id &&
            (predicate === '' || edge.type === predicate)
          );
        }).length > 0;
      }).flatMap((node) => node.type);
      return validPredicates;
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
                         if (concept.length === 0) concept.push('');
                         this.setState({ activeConcept : concept[0] }, () => {
                           const validPredicates = this._getValidProps(this.props.concepts,this.props.relations,true);
                           if (validPredicates.length === 0) {
                             this.setState({ activePredicate : '' });
                           }
                         });
                       }}
                       options={this._getValidProps(this.props.concepts,this.props.relations,false)}/>
          </div>
          <div>
            <span>Predicate (optional):</span>
            <Typeahead multiple={false}
                       id='browseNodePredicate'
                       placeholder={'Enter a biolink modal edge type...'}
                       onChange={(relation)=>{
                         if (relation.length === 0) relation.push('');
                         this.setState({ activePredicate : relation[0] }, () => {
                           const validNodes = this._getValidProps(this.props.concepts,this.props.relations,false);
                           if (validNodes.length === 0) {
                             this.setState({ activeConcept : '' });
                           }
                         });
                       }}
                       options={this._getValidProps(this.props.concepts,this.props.relations,true)}/>
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
