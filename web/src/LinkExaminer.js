import React, { Component } from 'react';
import { FaCircle, FaLongArrowAltLeft, FaLongArrowAltRight, FaTimes } from 'react-icons/fa';
import './LinkExaminer.css';

export default class LinkExaminer extends Component {
  constructor(props) {
    super(props);
  }
  render() {
    if (!this.props.render) return null;
    return (
      <div className="LinkExaminer">
        <div className="link-examiner-header horizontal-bar">
          <span className="link-examiner-header-text">Examine Connections</span>
          <FaTimes className="link-examiner-close-button" onClick={(e) => this.props.onClose(e)}/>
        </div>
        <div className="link-examiner-header-info">
          {
            [this.props.link.link.source, this.props.link.link.target]
              .sort((a,b)=>a.name.localeCompare(b.name))
              .map((node,i) => (
                <div className="header-node" key={i}>
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
              <div className="link-label" key={i} onClick={(e) => this.props.onLinkClick(link,e)}>
                <span title={link.source.name} style={{color:link.source.color}}>{link.source.name.slice(0,3).toUpperCase()}</span>
                <FaLongArrowAltRight/>
                <span className="link-label-text" style={{color:link.color}}>{link.type.join()}</span>
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
