import React, { Component } from 'react';
// import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import { Modal, Tabs, Tab } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
// import "react-tabs/style/react-tabs.css";

class Message extends Component {
  constructor(props, context) {
    super(props, context);
    this.state = {
      title: "",
      errors: [],
    };
    this.handleShow = this.handleShow.bind (this);
  }
  handleShow (title, errors) {
    if (typeof errors !== 'undefined') {
      errors.forEach((error) => {
        let { message, details } = error;
        if (details === undefined) details = "There is no advanced information about this error.";
        error.message = typeof message === "string" ? message.split ("\n").map((line,i) => <div key={i}><span>{line}</span><br/></div>) : message;
        error.details = typeof details === "string" ? details.split ("\n").map((line,i) => <div key={i}><span>{line}</span><br/></div>) : details;
      })
      this.setState({
        title : title,
        errors : errors
      });
    }
  }
  _errorTab(error) {
    return (
      <Tabs defaultActiveKey="message">
        <Tab eventKey="message" title="Message">
          {error.message}
        </Tab>
        <Tab eventKey="advanced" title="Advanced">
          {error.details}
        </Tab>
      </Tabs>
    )
  }
  render() {
    return (
      <>
        <Modal
          show={this.props.activeModal==="ErrorModal"}
          onHide={() => this.props.setActiveModal(null)}
          dialogClassName="messageDialog"
          aria-labelledby="example-custom-modal-styling-title"
        >
          <Modal.Header closeButton>
            <Modal.Title id="example-custom-modal-styling-title">
              {this.state.title}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {
              // It looks really ugly to have the nested tags when there's only one error so we'll get rid of them for a single error.
              this.state.errors.length > 1 ?
              (
                <Tabs defaultActiveKey="0">
                  {
                    this.state.errors.map((error,i) => (
                      <Tab eventKey={i.toString()} key={i} title={'Error '+(i+1).toString()}>
                        {this._errorTab(error)}
                      </Tab>
                    ))
                  }
                </Tabs>
              )
              :
              // We don't want to create an error tab when there are no errors
              (this.state.errors.length > 0 ? this._errorTab(this.state.errors[0]) : null)
            }
          </Modal.Body>
        </Modal>
      </>
    );
  }
}
export default Message;
