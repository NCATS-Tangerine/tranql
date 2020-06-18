import React, { Component } from 'react';
import { Form, Row, Col } from 'react-bootstrap';
import esToPrimitive from 'es-to-primitive';
import './InteractiveShell.css';

/**
 * Serves as an intermediary to facilitate interaction between the python and javascript environments.
 * - Acts as a provider of pertinent information such as the knowledge graph
 * - Also provides utility such as importing external modules
 *
 */
const Intermediary = function(controller) {
  return {
    install_module(module) {
      const start = Date.now();
      // Use a blocking promise
      return this.read_promise(new Promise((resolve) => {
        window.pyodide.loadPackage(module).then(() => {
          resolve(`Successfully installed ${module} in ${(Date.now() - start)/1000}s`);
        });
      }));
    },
    read_promise(promise) {
      controller.setBlock(true);
      const result = new BlockingPromise((resolve) => {
        promise.then((res) => {
          controller.setBlock(false);
          resolve(res);
        });
      });
      return result;
    }
  };
};

class BlockingPromise extends Promise {}

/**
 * Represents a message in the shell
 *
 */
class ShellMessage extends Component {
  static defaultProps = {
    prefix: ">>>\u00A0", // \u00A0 is the unicode literal for whitespace; property implemented for comprehensiveness
    message: "", // {string|React.Component}
    output: undefined, // {string|undefined|null} output of evalulated message - if promise, will display "Loading" until resolved
                       // undefined = no output
                       // null = empty line
    updatedContent: () => {} // since the text only displays after first render, parent component cannot scroll to bottom correctly
                             // maybe there's a better solution?
  };
  constructor(props) {
    super(props);
  }
  render() {
    return (
      <div className="shell-line">
        <div className="d-flex">
          <span className="line-prefix">
            {this.props.prefix}
          </span>
          <span className="line-content">
            {this.props.message}
          </span>
        </div>
        {
          <div className="line-output">{this.props.output === undefined ? null : (this.props.output === null ? <br/> : new String(this.props.output))}</div>
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

    this.setBlock = this.setBlock.bind(this);
    this._scrollToBottom = this._scrollToBottom.bind(this);
    this._publishMessage = this._publishMessage.bind(this);

    this._scrollContainer = React.createRef();
    this._input = React.createRef();
  }
  setBlock(blocking) {
    this.setState({
      loading : blocking
    })
  }
  _scrollToBottom() {
    if (this._scrollContainer.current !== null) this._scrollContainer.current.scrollTop = this._scrollContainer.current.scrollHeight;
  }
  _publishMessage(message) {
    const { messages } = this.state;
    messages.push(message);
    this.setState({
      messages
    });
  }
  componentDidUpdate() {
    this._scrollToBottom();
  }
  componentDidMount() {
    window.languagePluginLoader.then(() => {
      // Pyodide has to load the Python environment before it is usable; however, this happens so quickly that it is virtually impeceptible
      window.pyodide.globals.TranQL = new Intermediary({
        setBlock: this.setBlock
      });
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
        <Form onSubmit={async (e) => {
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
          const message = {
            message: input,
            output: result
          };
          if (result instanceof BlockingPromise) {
            message.promise = result;
            result.then((res) => {
              const { messages } = this.state;
              messages.forEach((msg) => {
                if (msg.promise === result) {
                  msg.output = res;
                }
              });
              this.setState({ messages });
            });
            message.output = null; // display an empty line instead of [object Promise] (null = empty line)
          }
          this._publishMessage(message);
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
