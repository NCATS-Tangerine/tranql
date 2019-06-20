import React, { Component } from 'react';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import { Modal } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import "react-tabs/style/react-tabs.css";

class Message extends Component {
  constructor(props, context) {
    super(props, context);
    this.state = {
      show: false,
      title: "",
      message: null,
      details: null,
    };
    this.handleHide = () => {
      this.setState({ show: false });
    };
    this.handleShow = this.handleShow.bind (this);
  }
  handleShow (title, message, details) {
    if (typeof message !== 'undefined' && typeof details !== 'undefined') {
      this.setState({
        show: true,
        title : title,
        message : typeof message === "string" ? message.split ("\n").map((line,i) => <div key={i}><span>{line}</span><br/></div>) : message,
        details : typeof details === "string" ? details.split ("\n").map((line,i) => <div key={i}><span>{line}</span><br/></div>) : details,
      });
    }
  }
  render() {
    return (
      <>
        <Modal
          show={this.state.show}
          onHide={this.handleHide}
          dialogClassName="messageDialog"
          aria-labelledby="example-custom-modal-styling-title"
        >
          <Modal.Header closeButton>
            <Modal.Title id="example-custom-modal-styling-title">
              {this.state.title}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <Tabs>
              <TabList>
                <Tab><b>Message</b></Tab>
                <Tab><b>Advanced</b></Tab>
              </TabList>
              <TabPanel>
                {this.state.message}
                <br/>
                <br/>
              </TabPanel>
              <TabPanel>
                {this.state.details}
                <br/>
                <br/>
              </TabPanel>
            </Tabs>
          </Modal.Body>
        </Modal>
      </>
    );
  }
}
export default Message;
