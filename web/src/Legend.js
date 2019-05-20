import React, { Component } from 'react';
import { Button } from 'reactstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

// Types
const NODE = 'node';
const LINK = 'link';

//Legend button component
class TypeButton extends Component {
  constructor(props) {
    super(props);

    this.state = {
      active:true,
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
      types:{
        nodeTypes: [
          this.nodeButton('testing'),
          this.nodeButton('test2')
        ],
        linkTypes: [
          this.linkButton('linktest')
        ]
      }
    };
  }

  typeButton(type, graphElementType) {
    return (<TypeButton type={type} graphElementType={graphElementType} />);
  }

  nodeButton(type) {
    return this.typeButton(type,NODE);
  }

  linkButton(type) {
    return this.typeButton(type,LINK);
  }

  render() {
    return (
      <div id={this.props.id} className="Legend">
        <div className="graphElementTypeContainer">
          {
            this.state.types.nodeTypes.map(nodeType => {
              return <div style={{display:'inline-block'}} key={nodeType.uniqueId}>{nodeType}</div>
            })
          }
        </div>
        <div className="graphElementTypeContainer">
          {
            this.state.types.linkTypes.map(linkType => {
              return <div style={{display:'inline-block'}} key={linkType.uniqueId}>{linkType}</div>
            })
          }
        </div>
      </div>
    );
  }
}

export default Legend;
