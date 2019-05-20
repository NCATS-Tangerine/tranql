import React, { Component } from 'react';
import { Button } from 'reactstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import './Legend.css';

// Types
const NODE = 'node';
const LINK = 'link';

//Legend button component
class TypeButton extends Component {
  constructor(props) {
    super(props);

    this.state = {
      active:this.props.visible,
      type: this.props.type,
      graphElementType: this.props.graphElementType
    };
  }

  render() {
    return (
      <Button className="TypeButton" active={this.state.active} size="sm">
        {this.props.graphElementType}: {this.state.type}
      </Button>
    );
  }
}


// Legend component
class Legend extends Component {
  constructor(props, context) {
    super(props, context);

    this.state = {
    };
  }

  typeButton(type, graphElementType) {
    // Instantiate TypeButton with given Node/Link type and given GraphElementType (Node/Link)
    return (<TypeButton type={type} graphElementType={graphElementType} />);
  }

  nodeButton(type) {
    return this.typeButton(type,NODE);
  }

  linkButton(type) {
    return this.typeButton(type,LINK);
  }

  render() {
    let graph = this.props.graph;
    console.log(graph);
    if (this.props.render && graph.nodes.length + graph.links.length != 0) {
      let nodes = graph.nodes;
      let links = graph.links;
      let nodeTypes = new Set();
      let linkTypes = new Set();
      nodes.forEach(node => {
        node.type.forEach(type => {
          nodeTypes.add(type);
        });
      });
      links.forEach(link => {
        linkTypes.add(link.type);
      });
      return (
        <>
          <div id={this.props.id} className="Legend">
            <div className="graphElementTypeContainer">
              {
                //How to generate unique id??
                Array.from(nodeTypes).map((nodeType,i) => {
                  return <div style={{display:'inline-block'}} key={i}>{this.nodeButton(nodeType)}</div>
                })
              }
            </div>
            <div className="graphElementTypeContainer">
              {
                Array.from(linkTypes).map((linkType,i) => {
                  return <div style={{display:'inline-block'}} key={i}>{this.linkButton(linkType)}</div>
                })
              }
            </div>
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
