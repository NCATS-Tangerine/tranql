import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import * as mime from 'mime-types';
import { Button } from 'reactstrap';
import { FilePond, registerPlugin } from 'react-filepond';
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type';
import './FileLoader.css';
import 'filepond/dist/filepond.min.css';
import 'bootstrap/dist/css/bootstrap.min.css';

registerPlugin(FilePondPluginFileValidateType);

export default class FileLoader extends Component {
  static defaultProps = {
    pondProps : {},
    buttonProps: {},
    buttonText: 'Confirm',
    filesLoadedCallback: () => {},
    loadFile: (fileType, data) => {return data;}
  };
  constructor(props) {
    super(props);

    this._filePond = React.createRef();
  }
  render() {
    return (
      <div className="FileLoader">
        <FilePond className="import-upload-area"
          {...this.props.pondProps}
          fileValidateTypeDetectType={(source,type)=>new Promise((resolve,reject) => {
            resolve('.' + source.name.split('.').pop());
          })}
          ref={(ref)=>{
            this._filePond = ref;
          }}
          beforeDropFile={((file)=>console.log(file))}
          oninit={() => {
            // Lots of hackery to get it to load URLs
            ReactDOM.findDOMNode(this._filePond).addEventListener('drop', async function(e) {
              e.preventDefault();
              let uri = e.dataTransfer.getData('text/uri-list');
              if (typeof uri === 'string' && uri.length > 0) {
                // eslint-disable-next-line
                if (!uri.match(/^\s*data:([a-z]+\/[a-z]+(;[a-z\-]+\=[a-z\-]+)?)?(;base64)?,[a-z0-9\!\$\&\'\,\(\)\*\+\,\;\=\-\.\_\~\:\@\/\?\%\s]*\s*$/i)) {
                  e.stopImmediatePropagation();
                  const toDataURL = function(blob) {
                    return new Promise((resolve,reject) => {
                      const fr = new FileReader();
                      fr.onload = (fr_e) => {
                        resolve(fr_e.target.result);
                      }
                      fr.onerror = (fr_e) => {
                        reject(fr_e);
                      }
                      fr.readAsDataURL(blob);
                    });
                  }
                  try {
                    const resp = await fetch(uri);
                    const blob = await resp.blob();
                    const url = await toDataURL(blob);
                    const urlPath = new URL(uri).pathname;
                    const extension = urlPath.split('.').pop() !== urlPath ? '' : '.' + mime.extension(resp.headers.get('content-type'));
                    this._filePond.addFile(new File([blob],urlPath.split('/').pop()+extension));
                  }
                  catch {
                    this._filePond.addFile('https://www.google.com/test.jpeg');
                  }
                  ReactDOM.findDOMNode(this._filePond).querySelector('.filepond--root').removeAttribute('data-hopper-state');
                  ReactDOM.findDOMNode(this._filePond).querySelector('.filepond--drip').style.display = "none";
                }
              }
            }.bind(this),true);
        }}>
        </FilePond>
        <Button {...this.props.buttonProps}
                color="primary"
                onClick={(() => {
                  let files = this._filePond.getFiles();
                  let loaded = [];
                  files.forEach((file) => {
                    if (!file) return;
                    loaded.push(new Promise((resolve,reject) => {
                      const fr = new FileReader();
                      fr.onload = (e) => {
                        let data = e.target.result;
                        let mimeType = mime.lookup(file.filename);
                        let message = this.props.loadFile(mimeType,data,file);
                        resolve(message);
                      };
                      fr.readAsText(file.file);
                    }));
                  });
                  Promise.all(loaded).then((files) => {
                    this.props.filesLoadedCallback(files);
                  });
                })}>{this.props.buttonText}</Button>
      </div>
    )
  }
}
