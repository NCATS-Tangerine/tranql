import React, { Component } from 'react';
import { Form, Row, Col } from 'react-bootstrap';
import esToPrimitive from 'es-to-primitive';
import './InteractiveShell.css';

class ShellMessage extends Component {
  static defaultProps = {
    prefix: ">>>\u00A0", // \u00A0 is the unicode literal for whitespace; property implemented for comprehensiveness
    message: "", // {string|React.Component|Promise} - if type Promise, will display loading until resolved
    output: null, // output of evalulated message,
    updatedContent: () => {} // since the text only displays after first render, parent component cannot scroll to bottom correctly
                             // maybe there's a better solution?
  };
  constructor(props) {
    super(props);

    this.state = {
      resolvedMessage: null
    };
  }
  componentDidMount() {
    Promise.resolve(this.props.message).then((resolvedMessage) => {
      this.setState({ resolvedMessage });
      this.props.updatedContent();
    });
  }
  render() {
    return (
      <div className="shell-line">
        {
          this.state.resolvedMessage !== null ? (
            <>
            <div className="d-flex">
              <span className="line-prefix">
                {this.props.prefix}
              </span>
              <span className="line-content">
                {this.state.resolvedMessage}
              </span>
            </div>
            {this.props.output != null && (<div className="line-output">{this.props.output}</div>)}
            </>
          ) : (
            <span>Loading...</span>
          )
        }
      </div>
    );
  }
}

export default class InteractiveShell extends Component {
  static defaultProps = {
  };
  constructor(props) {
    super(props);

    this.state = {
      loading: true,
      messages: [
        {
          message: <span className="loading">Bootstraping Python environment</span>
        }
      ]
    };

    // Tracks timestamp when initialized for loading time calculation
    this._timeOfInit = Date.now();

    this._scrollToBottom = this._scrollToBottom.bind(this);

    this._scrollContainer = React.createRef();
    this._input = React.createRef();
  }
  _scrollToBottom() {
    if (this._scrollContainer.current !== null) this._scrollContainer.current.scrollTop = this._scrollContainer.current.scrollHeight;
  }
  componentDidUpdate() {
    this._scrollToBottom();
  }
  componentDidMount() {
    window.languagePluginLoader.then(() => {
      // Pyodide has to load the Python environment before it is usable; however, this happens so quickly that it is virtually impeceptible
      this.setState({
        loading : false,
        messages : []
      }, () => {
        // Problem with keys, React does not recognize that this message is new without removing previous because they're assigned the same key
        this.setState({
          messages : [
            {
              message: "Finished bootstraping Python environment. Loaded in " + (Date.now() - this._timeOfInit)/1000 + "s"
            }
          ]
        })
      });
    });
  }
  render() {
    if (!this.props.active) return null;
    return (
      <div className="InteractiveShell" ref={this._scrollContainer}>
        <Form onSubmit={(e) => {
          e.preventDefault();

          const input = this._input.current.value;
          const { messages } = this.state;
          let result = null;
          try {
            result = window.pyodide.runPython(input);
          }
          catch (error) {
            result = error.message;
          }
          this.setState({
            messages: messages.concat({
              message: input,
              output: esToPrimitive(result)
            })
          });
          this._input.current.value = "";
        }}>
          {this.state.messages.map(({ message, output }, i) => {
            return <ShellMessage message={message} output={output} updatedContent={this._scrollToBottom} key={i}/>;
          })}
          {!this.state.loading && <ShellMessage message={
            <Form.Control type="text" spellCheck={false} autoFocus plaintext className="p-0" style={{border: "none", outline: "none"}} ref={this._input}/>
          }/>}
        </Form>
      </div>
    );
  }
}
