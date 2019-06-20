import React, { Component } from 'react';
import { Modal } from 'react-bootstrap';
import { FaSpinner } from 'react-icons/fa';
import 'bootstrap/dist/css/bootstrap.min.css';

class AnswerViewer extends Component {
  constructor(props, context) {
    super(props, context);

    this.state = {
      show: false,
      answerUrl : null,
      loaded : false
    };
    this.handleHide = () => {
      this.setState({ show: false });
    };
    this.handleShow = this.handleShow.bind (this);
  }
  handleShow (url) {
    this.setState({ show: true, answerUrl : url, loaded : false });
  }
  render() {
    return (
      <>
        <Modal
          show={this.state.show}
          onHide={this.handleHide}
          dialogClassName="answerNavigator"
          aria-labelledby="example-custom-modal-styling-title"
        >
          <Modal.Header closeButton>
            <Modal.Title id="example-custom-modal-styling-title" style={{display:"flex",alignItems:"center"}}>
              {!this.state.loaded && <FaSpinner style={{marginRight:"15px", marginLeft:"5px", fontSize:"24px"}} className="fa-spin"/>}
              Answer Navigator
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <iframe src={this.state.answerUrl}
                    height={"100%"} width={"100%"}
                    frameBorder={"0"}
                    onLoad={()=>this.setState({ loaded : true })}
            />
          </Modal.Body>
        </Modal>
      </>
    );
  }
}
export default AnswerViewer;
