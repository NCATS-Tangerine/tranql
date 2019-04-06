import React, { Component } from 'react';
import { Modal } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

class AnswerViewer extends Component {
  constructor(props, context) {
    super(props, context);

    this.state = {
      show: false,
      answerUrl : null,
    };
    this.handleHide = () => {
      this.setState({ show: false });
    };
    this.handleShow = this.handleShow.bind (this);
  }
  handleShow (url) {
    this.setState({ show: true, answerUrl : url });
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
            <Modal.Title id="example-custom-modal-styling-title">
              Answer Navigator
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <iframe src={this.state.answerUrl}
                    height={"100%"} width={"100%"}
                    frameBorder={"0"}
            />
          </Modal.Body>
        </Modal>
      </>
    );
  }
}
export default AnswerViewer;
