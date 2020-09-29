import React, { Component } from 'react';
import { FaHistory } from 'react-icons/fa';
import { Modal, ListGroup, Container, Row, Table } from 'react-bootstrap';
import './HistoryViewer.css';

export default class HistoryViewer extends Component {
  constructor(props) {
    super(props);

    this.state = {
      queries: null
    };
  }
  componentDidMount() {
    this.props.cache.db.cache.toArray().then((queries) => {
      this.setState({ queries : queries.sort((a, b) => b.timestamp - a.timestamp) });
    });
  }
  render() {
    const closeModal = () => this.props.setActiveModal(null);
    return (
      <>
      <FaHistory className="HistoryViewer-inactive" onClick={() => this.props.setActiveModal("HistoryViewer")}/>
      <Modal show={this.props.activeModal === "HistoryViewer"}
             onHide={closeModal}
             dialogClassName="history-viewer-dialog">
        <Modal.Header closeButton>
          <Modal.Title>History Viewer</Modal.Title>
        </Modal.Header>
        <Modal.Body style={{display: "flex", "overflow-y": "auto"}}>
          <Container fluid={true} style={{height: "100%"}}>
            <Row style={{display: "block", height: "100%"}}>
              {this.state.queries === null ? (
                <div>Loading queries.</div>
              ) : (
                <Table striped bordered hover>
                  <thead>
                    <tr style={{display: "none"}}><th>Query</th></tr>
                  </thead>
                  <tbody>
                    {this.state.queries.map((query) => (
                        <tr onClick={() => {
                          this.props.setCode(query.key);
                          closeModal();
                        }}>
                          <td>{query.key}</td>
                        </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Row>
          </Container>
        </Modal.Body>
      </Modal>
      </>
    );
  }
}
