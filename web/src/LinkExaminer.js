import React, { Component } from 'react';
import { FaCircle, FaLongArrowAltLeft, FaLongArrowAltRight } from 'react-icons/fa';
import './LinkExaminer.css';

export default class LinkExaminer extends Component {
  constructor(props) {
    super(props);
  }
  render() {
    if (!this.props.render) return null;
    return (
      <div className="LinkExaminer">
        <div className="link-examiner-header">
          <h6 className="link-examiner-header-text">Examine Connections</h6>
        </div>
        <div className="link-examiner-header-info">
          {
            [this.props.link.link.source, this.props.link.link.target]
              .sort((a,b)=>a.name.localeCompare(b.name))
              .map((node) => (
                <div className="header-node">
                  <FaCircle color={node.color}/>
                  <span>{node.name}</span>
                </div>
              ))
          }
        </div>
        {
          /*
           * <span>{link.source.name.split("_").map(str=>str.charAt(0)).join("").toUpperCase()}</span>
           * <span title={link.target.name} style={{color:link.target.color}}>{link.target.name.slice(0,10)+(link.target.name.length > 10 ? "..." : "")}</span>
           */
          this.props.link.link.allConnections.map((link, i) => {
            return (
              <div className="link-label" key={i}>
                <span title={link.source.name} style={{color:link.source.color}}>{link.source.name.slice(0,3).toUpperCase()}</span>
                <FaLongArrowAltRight/>
                {link.type.join()}
                <FaLongArrowAltRight/>
                <span title={link.target.name} style={{color:link.target.color}}>{link.target.name.slice(0,3).toUpperCase()}</span>
              </div>
            );
          })
        }
      </div>
    );
  }
}
