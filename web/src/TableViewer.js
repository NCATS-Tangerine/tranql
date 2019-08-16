import React, { Component } from 'react';
import { Button } from 'reactstrap';
import { Form, Tabs, Tab } from 'react-bootstrap';
import * as YAML from 'js-yaml';
import ReactTable from 'react-table';
import './TableViewer.css';


export default class TableViewer extends Component {
  static defaultProps = {
    onOpen: () => {},
    onClose: () => {},
    resetAttributesOnOpen : true,
    filterButtonProps : {},
    closeButtonProps : {},
    tableProps: {},
    searchMethod : null,
    buttons : []
  };
  /**
   * Constructs a new table viewer.
   *
   * @param {Object} props - Properties of the table viewer
   * @param {Function} [props.onOpen=function(){}] - Callback invoked when TableViewer::open is called.
   * @param {Function} [props.onClose=function(){}] - Callback invoked when TableViewer::close is called.
   * @param {Object<String,T[]>} data - The data to be represented in the table viewer. The object's keys will be used as tabs.
   * @param {Object} defaultTableAttributes - Default attributes that display for each tab. Every key in the `data` prop must be included.
   * @param {Boolean} [resetAttributesOnOpen=true] - Specifies if the `tableAttributes` state property will be reset
   *    to the `defaultTableAttributes` prop whenever the table is opened.
   * @param {Object} [filterButtonProps={}] - Props to pass to the filter button. Overrides the props that TableViewer passes to it.
   * @param {Object} [closeButtonProps={}] - Props to pass to the close button. Overrides the props that TableViewer passes to it.
   * @param {Object} [tableProps={}] - Props to pass to the react-table instance. Overrides the props that TableViewer passes to it.
   * @param {Function|null} [searchMethod=null] - Override TableViewer's default search method. Refer to the ReactTable prop `defaultFilterMethod` for usage.
   * @param {React.Component[]|React.Component} [buttons=[]] - Injects components into the button container. Recommended: reactstrap Button with size="sm".
   */
  constructor(props) {
    super(props);

    this.state = {
      tableView : false,
      tableFilterView : false,
      tableAttributes : this.props.defaultTableAttributes,
      filterFilter : ''
    };

    this._tabs = React.createRef();
    this._filterInputFilter = React.createRef();

    this.open = this.open.bind(this);
    this.close = this.close.bind(this);
    this.toggleVisibility = this.toggleVisibility.bind(this);
    this.resetAttributes = this.resetAttributes.bind(this);
    this._getActiveTabName = this._getActiveTabName.bind(this);
  }
  resetAttributes() {
    this.setState({ tableAttributes : this.props.defaultTableAttributes });
  }
  toggleVisibility() {
    this.state.tableView ? this.close() : this.open();
  }
  open() {
    const resetAttrsObj = this.state.resetAttributesOnOpen ? {tableAttributes : this.props.defaultTableAttributes} : {};
    this.setState({ tableView : true, ...resetAttrsObj });
    this.props.onOpen();
  }
  close() {
    this.setState({ tableView : false });
    this.props.onClose();
  }
  _getActiveTabName() {
    return this._tabs.current.props.activeKey;
  }
  render() {
    if (!this.state.tableView) return null;
    return (
      <div className="TableViewer">
        <div className="table-viewer-button-container">
          {
            this.state.tableFilterView && (<Form.Control className="form-inline" type="text" ref={ref => {this._filterInputFilter = ref;}} onChange={() => {
              const value = this._filterInputFilter.value;
              this.setState({ filterFilter : value });
            }}/>)
          }
          {this.props.buttons}
          {
            this.state.tableFilterView && (<Button className="table-viewer-filter-button" size="sm" color="warning" onClick={() => {
              const tableAttributes = this.state.tableAttributes;
              tableAttributes[this._getActiveTabName()] = [];
              this.setState({ tableAttributes });
            }}>
              Uncheck all
            </Button>)
          }
          <Button className="table-viewer-filter-button" size="sm" color={this.state.tableFilterView?"secondary":"primary"} onClick={() => {
            this.setState({ tableFilterView : !this.state.tableFilterView });
          }} {...this.props.filterButtonProps}>
            {this.state.tableFilterView ? "Back" : "Filter"}
          </Button>
          <Button className="table-viewer-close-button" size="sm" color="danger" onClick={() => this.close()} {...this.props.closeButtonProps}>Close</Button>
        </div>
        <Tabs defaultActiveKey={Object.keys(this.props.data)[0]} ref={this._tabs}>
          {
            (() => {
              const elementTypes = Object.keys(this.props.data);
              return elementTypes.map((elementType,index) => (
                <Tab eventKey={elementType} title={elementType} key={index.toString()}>
                  {
                    (() => {
                      const graph = this.props.data;
                      const elements = graph[elementType];
                      const keys = elements.flatMap((el) => Object.keys(el)).unique()

                      // const serialize = (object) => {
                      //   if (Array.isArray(object)) {
                      //     return <div>{object.map((obj) => <>{serialize(obj)}<br/></>)}</div>;
                      //   }
                      //   else if (typeof object === "object") {
                      //     return (<div>{Object.entries(object).map((object) => {
                      //       return <>{serialize(object[0])} = {serialize(object[1])}}<br/></>;
                      //     })}</div>);
                      //   }
                      //   else {
                      //     return <div>{object}</div>;
                      //   }
                      // }
                      if (this.state.tableFilterView) {
                        return (
                          <div className="table-filter-container">
                            {
                              keys.filter((key) => key.startsWith(this.state.filterFilter)).map((key,i) => (
                                  <Form.Check
                                      type="checkbox"
                                      label={key}
                                      key={i}
                                      inline
                                      checked={this.state.tableAttributes[elementType].includes(key)}
                                      onChange={()=>{
                                        const tableAttributes = this.state.tableAttributes;
                                        const index = tableAttributes[elementType].indexOf(key);
                                        if (index !== -1) {
                                          tableAttributes[elementType].splice(index,1);
                                        }
                                        else {
                                          tableAttributes[elementType].push(key);
                                        }
                                        this.setState({ tableAttributes });
                                      }}
                                  />
                              ))
                            }
                          </div>
                        );
                      }
                      else {
                        const columns = keys.filter((key) => this.state.tableAttributes[elementType].includes(key)).map((key,i) => {
                          return ({
                            Header: key,
                            accessor: (el) => typeof el[key] === "object" ? YAML.safeDump(el[key]) : el[key],
                            id:key
                          });
                        });
                        return (
                          <ReactTable data={elements}
                                      columns={columns}
                                      defaultPageSize={15}
                                      filterable
                                      defaultFilterMethod={(filter,row) => {
                                        if (this.props.searchMethod !== null) {
                                          return this.props.searchMethod(filter,row);
                                        }
                                        const attributeValue = row[filter.id];
                                        if (typeof attributeValue === 'undefined') {
                                          // If the object doesn't have this attribute just don't include it.
                                          return false;
                                        }
                                        const isRegexLiteral = filter.value.match(/^\/(.*)\/([g|i|m|u|y]*)$/);
                                        if (isRegexLiteral !== null) {
                                          try {
                                            const expr = isRegexLiteral[1];
                                            const flags = isRegexLiteral[2];
                                            const re = new RegExp(expr,flags);
                                            return attributeValue.match(re);
                                          }
                                          catch {
                                            // Return false if the regex is invalid
                                            return false;
                                          }
                                        }
                                        return attributeValue.includes(filter.value);
                                      }}
                                      className="-striped -highlight"
                                      {...this.props.tableProps}/>
                        );
                      }
                    })()
                  }
                </Tab>
              ));
            })()
          }
        </Tabs>
      </div>
    );
  }
}
