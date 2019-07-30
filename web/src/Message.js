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
      errors: [],
    };
    this.handleHide = () => {
      this.setState({ show: false });
    };
    this.handleShow = this.handleShow.bind (this);
  }
  handleShow (title, errors) {
    if (typeof errors !== 'undefined') {
      errors.forEach((error) => {
        const { message, details } = error;
        if (details === undefined) details = "There is no advanced information about this error.";
        error.message = typeof message === "string" ? message.split ("\n").map((line,i) => <div key={i}><span>{line}</span><br/></div>) : message;
        error.details = typeof details === "string" ? details.split ("\n").map((line,i) => <div key={i}><span>{line}</span><br/></div>) : details;
      })
      this.setState({
        show: true,
        title : title,
        errors : errors
      });
    }
  }
  _errorTab(error) {
    return (
      <Tabs>
        <TabList>
          <Tab><b>Message</b></Tab>
          <Tab><b>Advanced</b></Tab>
        </TabList>
        <TabPanel>
          {error.message}
        </TabPanel>
        <TabPanel>
          {error.details}
        </TabPanel>
      </Tabs>
    )
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
            {
              // It looks really ugly to have the nested tags when there's only one error so we'll get rid of them for a single error.
              this.state.errors.length > 1 ?
              (
                <Tabs>
                  <TabList>
                    {
                      this.state.errors.map((error,i) => (
                        <Tab key={i}>Error {i+1}</Tab>
                      ))
                    }
                  </TabList>
                  {
                    this.state.errors.map((error,i) => (
                      <TabPanel key={i}>
                        {this._errorTab(error)}
                      </TabPanel>
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
