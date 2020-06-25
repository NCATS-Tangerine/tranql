import React, { Component } from 'react';
import { Form, Row, Col, ToggleButton, ToggleButtonGroup, Button, Tabs, Tab } from 'react-bootstrap';
import { Controlled as CodeMirror } from 'react-codemirror2';
import { FaPlus, FaTimes } from 'react-icons/fa';
import * as qs from 'qs';
import * as JSON5 from 'json5';
import * as classNames from 'classnames';
import esToPrimitive from 'es-to-primitive';
import 'codemirror/mode/python/python';
import './InteractiveShell.css';

// Used for naming programs
let PROGRAM_COUNT = 0;

/**
 * Serves as an intermediary to facilitate interaction between the python and javascript environments.
 * - Acts as a provider of pertinent information such as the knowledge graph
 * - Also provides utility such as importing external modules
 *
 */
function Intermediary(controller, pyodide_module) {
  // let _WATCHING_OBJECTS = true;

  const public_intermediary = {
    // Offers important Promise utilities such as `all`
    promise: {
      all(promises) {
        return Promise.all(promises);
      },
      race(promises) {
        return Promise.race(promises);
      }
    },
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
    make_query(query, KnowledgeGraph) {
      // Return a promise of a python KnowledgeGraph class
      return new Promise((resolve) => {
        const { queryData } = controller
        // Don't bother trying to reuse how App executes a query, it is too difficult to isolate the logic from state updates
        let message = null;
        var cachePromise = queryData.useCache ? queryData._cache.read ('cache', 'key', query) : Promise.resolve ([]);
        cachePromise.then (
          function success (result) {
            if (result.length > 0) {
              // Translate the knowledge graph given current settings.
              resolve(KnowledgeGraph(result[0].data.knowledge_graph));
            }
            else {
              const args = {
                'dynamic_id_resolution' : queryData.dynamicIdResolution,
                'asynchronous' : true
              };
              fetch(queryData.tranqlURL + '/tranql/query?'+qs.stringify(args), {
                method: "POST",
                headers: {
                  'Accept': 'application/json',
                  'Content-Type': 'text/plain',
                },
                body: query
              }).then(res => res.text())
              .then(
                (result) => {
                  resolve(
                    KnowledgeGraph(JSON5.parse(result).knowledge_graph)
                  );
                },
                (error) => { throw error; }
              );
            }
          },
          function error (error) {
            throw error;
          }
        );
      });
    },
    // properties
    get_knowledge_graph() {
      // Deep copy knowledge_graph
      return controller.data.message ? JSON.parse(JSON.stringify(controller.data.message.knowledge_graph)) : null;
    },
    set_knowledge_graph(knowledge_graph) {
      controller.data.set_knowledge_graph(knowledge_graph)
    }
  };

  // Inject the intermediary into Pyodide
  window.pyodide.globals.TranQL = public_intermediary;
  // Evaluate the module for Pyodide
  window.pyodide.runPython(pyodide_module);
  // Remove the intermediary
  try {delete window.pyodide.globals.TranQL;} catch {}

  // Return a way for the controller's state to get updated
  return function updateController(newController) {
    controller = newController;
  }
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
    // let val;
    // try {
    //   val = this.props.output.constructor.name+"<"+JSON.stringify(this.props.output)+">";
    // }
    // catch {}
    // if (typeof val === "undefined") val = new String(this.props.output);
    // return val;

    return this.props.output.toString();
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
          message: <span>Bootstraping Python environment. May cause delays and temporary unresponsiveness.</span>
        }
      ],
      lineBuffer: [],

      repl: true, // determines if in REPL mode or script mode,
      programs: [this._programSkeleton()], // editor programs, start with one empty program
      activeProgram: 0  // active editor program (index)
    };

    // Tracks timestamp when initialized for loading time calculation
    this._timeOfInit = Date.now();

    // Method to update data within the intermediary
    this._updateIntermediary = null;

    // Module installation, scripts, etc. will not be loaded until the first time Pyodide is opened
    // This avoids the website freezing for loading purposes unless the user intends to use the shell
    this._loadedPyodide = false;

    this.setBlock = this.setBlock.bind(this);
    this._scrollToBottom = this._scrollToBottom.bind(this);
    this._publishMessage = this._publishMessage.bind(this);
    this._getControllerData = this._getControllerData.bind(this);
    this._isLineBufferActive = this._isLineBufferActive.bind(this);
    this._renderRepl = this._renderRepl.bind(this);
    this._renderEditor = this._renderEditor.bind(this);
    this._renderToggleGroup = this._renderToggleGroup.bind(this);
    this._addProgram = this._addProgram.bind(this);
    this._hookPyodide = this._hookPyodide.bind(this);
    this._loadPyodide = this._loadPyodide.bind(this);

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
      // Anything from App that is explicitly required in the `make_query` method
      queryData: this.props.queryData,
      data: this.props.data
    };
  }
  _isLineBufferActive() {
    return this.state.lineBuffer.length > 0;
  }
  _renderRepl() {
    return (
      <>
      <div className={classNames("shell-btn-container", !this.state.repl && "menu")}>
        {this._renderToggleGroup()}
      </div>
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
      </>
    );
  }
  _renderEditor() {
    return (
      <div className="editor">
        {
          this.state.programs.length === 0 ? (
            null
          ) : (
            <>
            <div className={classNames("shell-btn-container", !this.state.repl && "menu")}>
              <div className="editor-menu-left">
                <Tabs activeKey={this.state.activeProgram} onSelect={(key) => this.setState({ activeProgram : key })}>
                {
                  this.state.programs.map((program, i) => {
                    const { programName } = program;
                    const isActive = i == this.state.activeProgram;
                    return (
                      <Tab eventKey={i} key={i} title={
                        <>
                        <span>{programName}</span>
                        {isActive && <FaTimes className="close-program" onClick={(e) => {
                          // Have to call preventDefault here or else after this is done the onSelect handler in <Tabs> will get ahold of it
                          // if the rightmost tab is being deleted, it will set `activeProgram` back to the previous value causing an error
                          e.preventDefault();
                          e.stopPropagation();
                          this.setState({
                            programs: this.state.programs.slice(0, i).concat(this.state.programs.slice(i+1)),
                            // If you delete the rightmost program activeProgram will not point to anything, causing an error
                            activeProgram: (this.state.activeProgram == this.state.programs.length-1 ? this.state.activeProgram - 1 : this.state.activeProgram)
                          });
                        }}/>}
                        </>
                      }></Tab>
                    );
                  })
                }
                </Tabs>
                <FaPlus className="add-program-btn" data-tip="Create a program" onClick={() => {
                  this._addProgram();
                }}/>
              </div>
              <div className="editor-menu-right">
                <Button className="editor-run-btn" variant="outline-success" disabled={this.state.programs.length === 0} onClick={() => {
                  const program = this.state.programs[this.state.activeProgram];
                  let result;
                  try {
                    result = window.pyodide.runPython(program.programCode);
                  }
                  catch (error) {
                    result = error.message;
                  }
                  this.setState({ repl : true });
                  this._publishMessage({
                    message: `Executing editor program "${program.programName}"`,
                    output: result
                  });
                }}>Run</Button>
                {this._renderToggleGroup()}
              </div>
            </div>
            <CodeMirror value={this.state.programs[this.state.activeProgram].programCode}
                        options={{
                          lineNumbers: true,
                          mode: "python",
                          tabSize: 4,
                          readOnly: false
                        }}
                        onBeforeChange={(editor, data, value) => {
                          const { programs } = this.state;
                          programs[this.state.activeProgram].programCode = value;
                          this.setState({ programs });
                        }}
                        onChange={(editor, data, value) => {}}/>
            </>
          )
        }
      </div>
    );
  }
  _programSkeleton() {
    return {
      programName: "Program " + (++PROGRAM_COUNT),
      programCode: ""
    };
  }
  _addProgram() {
    const { programs } = this.state;
    programs.push(this._programSkeleton());
    this.setState({
      programs,
      activeProgram : programs.length - 1
    });
  }
  _renderToggleGroup() {
    return (
      <ToggleButtonGroup className="shell-btn-group" type="radio" name="editor-types" value={this.state.repl} onChange={(val) => this.setState({ repl : val })}>
        <ToggleButton value={true}>Shell</ToggleButton>
        <ToggleButton value={false}>Editor</ToggleButton>
      </ToggleButtonGroup>
    );
  }
  _hookPyodide(pyodideModule) {
    const updateIntermediary = new Intermediary(this._getControllerData(), pyodideModule);
    this._updateIntermediary = updateIntermediary;
    // window.pyodide.globals.TranQL = intermediary;
  }
  async _loadPyodide() {
    this._loadedPyodide = true;
    // Pyodide has to load the Python environment before it is usable; however, this happens so quickly that it is virtually impeceptible
    const response = await fetch(this.props.queryData.tranqlURL + '/tranql/pyodide_module', {
      method: "GET"
    });
    const pyodideModule = JSON.parse(await response.text());
    await window.languagePluginLoader;
    await window.pyodide.loadPackage(['networkx']); // the primary blockage occurs when the packages are actually imported
    this._hookPyodide(pyodideModule);
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
  }
  componentDidUpdate() {
    this.state.repl && this._scrollToBottom();
    // If the shell is now active and Pyodide features have not been loaded, load them
    this.props.active && !this._loadedPyodide && this._loadPyodide();
    this._updateIntermediary != null && this._updateIntermediary(this._getControllerData());
  }
  componentWillUnmount() {
    // window.languagePluginLoader.then(() => {
    //   try {
    //     if ("TranQL" in window.pyodide.globals) window.pyodide.globals.TranQL = undefined;
    //   }
    //   catch {}
    // });
  }
  render() {
    if (!this.props.active) return null;
    return (
      <div className="InteractiveShell" ref={this._scrollContainer}>
        {this.state.repl ? this._renderRepl() : this._renderEditor()}
      </div>
    );
  }
}
