import React, { Component } from 'react';
import { Form, Row, Col } from 'react-bootstrap';
import * as classNames from 'classnames';
import esToPrimitive from 'es-to-primitive';
import './InteractiveShell.css';

/**
 * Serves as an intermediary to facilitate interaction between the python and javascript environments.
 * - Acts as a provider of pertinent information such as the knowledge graph
 * - Also provides utility such as importing external modules
 *
 */
function Intermediary(controller) {
  // let _WATCHING_OBJECTS = true;

  const public_intermediary = {
    install_module(module) {
      const start = Date.now();
      controller.setBlock(true);
      window.pyodide.loadPackage(module).then(() => {
        controller.setBlock(false);
        controller.publishMessage({
          message: `Successfully installed ${module} in ${(Date.now() - start)/1000}s`
        });
      });
      return null;
    },
    dumps(obj) {
      return JSON.stringify(obj);
    },
    // properties
    get_knowledge_graph() {
      return controller.data.message ? controller.data.message.knowledge_graph : null;
    },
    export_changes() {
      controller.data.set_knowledge_graph(this.get_knowledge_graph());
    }
    // get_WATCHING_OBJECTS() {
    //   return _WATCHING_OBJECTS;
    // },
    // set_WATCHING_OBJECTS(watch) {
    //   _WATCHING_OBJECTS = watch;
    // }
  };
  const private_intermediary = {
    updateController(newController) {
      controller = newController;
    }
  };
  return [
    public_intermediary,
    private_intermediary
  ];
};

/**
 * Represents a message in the shell
 *
 */
class ShellMessage extends Component {
  static defaultProps = {
    prefix: ">>>\u00A0", // \u00A0 is the unicode literal for whitespace; property implemented for comprehensiveness
    fakePrefix: undefined, // Allows for mimicing the width of `fakePrefix`
                           // Basically the element has whatever width it would have should `prefix` have the value of `fakePrefix`,
                           // but it displays the value of `prefix` instead. Used for the "..." prefix which is much shorter than the ">>> " prefix
                           // to make the text align correctly
    message: "", // {string|React.Component}
    output: undefined, // {string|undefined|null} output of evalulated message - if promise, will display "Loading" until resolved
                       // undefined = no output
    updatedContent: () => {} // since the text only displays after first render, parent component cannot scroll to bottom correctly
                             // maybe there's a better solution?
  };
  constructor(props) {
    super(props);

    this._getSanitizedOutput = this._getSanitizedOutput.bind(this);
  }
  _getSanitizedOutput() {
    if (this.props.output === undefined) return null;
    try {
      return JSON.stringify(this.props.output);
    }
    catch {
      return new String(this.props.output);
    }
  }
  render() {
    const useFakePrefix = this.props.fakePrefix !== undefined;
    const fakePrefix = this.props.fakePrefix;
    return (
      <div className="shell-line">
        <div className="d-flex">
          <span className={classNames("line-prefix", useFakePrefix && "invisible")}>
            {
              /**
               * If a fake prefix is set, give the line-prefix class visibility: hidden so that it doesn't display the fake prefix,
               * but still assumes its width.
               *
               * If a fake prefix is set, use the fake prefix's text here so that it assumes the width of the fake prefix.
               * The actual text will be displayed via the following span which has an absolute position.
               */
              useFakePrefix ? fakePrefix : this.props.prefix
            }
          </span>
          {
            useFakePrefix && <span className="real-prefix">{this.props.prefix}</span>
          }
          <span className="line-content">
            {this.props.message}
          </span>
        </div>
        {
          <div className="line-output">{this._getSanitizedOutput()}</div>
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
      ],
      lineBuffer: []
    };

    // Tracks timestamp when initialized for loading time calculation
    this._timeOfInit = Date.now();

    this._privateIntermediary = null;

    this.setBlock = this.setBlock.bind(this);
    this._scrollToBottom = this._scrollToBottom.bind(this);
    this._publishMessage = this._publishMessage.bind(this);
    this._getControllerData = this._getControllerData.bind(this);
    this._isLineBufferActive = this._isLineBufferActive.bind(this);

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
  _getControllerData() {
    return {
      setBlock: this.setBlock,
      publishMessage: this._publishMessage,
      data: this.props.data
    };
  }
  _isLineBufferActive() {
    return this.state.lineBuffer.length > 0;
  }
  componentDidUpdate() {
    this._scrollToBottom();
    this._privateIntermediary != null && this._privateIntermediary.updateController(this._getControllerData());
  }
  componentWillUnmount() {
    window.languagePluginLoader.then(() => {
      if ("TranQL" in window.pyodide.globals) delete window.pyodide.globals.TranQL;
    });
  }
  componentDidMount() {
    // Pyodide has to load the Python environment before it is usable; however, this happens so quickly that it is virtually impeceptible
    window.languagePluginLoader.then(() => {
      const [ intermediary, privateIntermediary ] = new Intermediary(this._getControllerData());
      this._privateIntermediary = privateIntermediary;
      window.pyodide.globals.TranQL = intermediary;
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

          let input = this._input.current.value;
          // \n indicates to use line buffer for multiline statement
          const useBuffer = input.slice(input.length - 2, input.length) == "\\n";

          if (useBuffer) {
            // Truncate ending newline
            input = input.slice(0, input.length - 2);
            this._publishMessage({
              message: input,
              prefix: this._isLineBufferActive() ? ". . ." : undefined,
              fakePrefix: this._isLineBufferActive() ? ">>>\u00A0" : undefined
            });
            this.setState({ lineBuffer : this.state.lineBuffer.concat(input) });
          }
          else {
            const { messages } = this.state;
            let result = null;
            try {
              const { lineBuffer } = this.state;
              if (lineBuffer.length > 0) {
                // Empty line buffer
                this.setState({ lineBuffer : [] });
                // Push input to end of line buffer and join it by newlines for pyodide
                input = lineBuffer.concat(input).join("\n");
              }
              result = window.pyodide.runPython(input);
            }
            catch (error) {
              result = error.message;
            }
            this._publishMessage({
              message: input,
              output: result
            });
          }

          this._input.current.value = "";
        }}>
          {this.state.messages.map((message, i) => {
            return <ShellMessage {...message} updatedContent={this._scrollToBottom} key={i}/>;
          })}
          {!this.state.loading && <ShellMessage prefix={this._isLineBufferActive() ? ". . ." : undefined}
                                                fakePrefix={this._isLineBufferActive() ? ">>>\u00A0" : undefined}
                                                message={
                                                  <Form.Control type="text"
                                                                spellCheck={false}
                                                                autoFocus
                                                                plaintext
                                                                className="p-0"
                                                                style={{border: "none", outline: "none"}}
                                                                ref={this._input}/>
                                                }/>
          }
        </Form>
      </div>
    );
  }
}
