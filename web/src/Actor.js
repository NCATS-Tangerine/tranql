class Actor { //extends Component {
/*  constructor(props) {
    super(props);
  }
*/
  constructor(app) {
    this.app = app;
  }
  handle (message) {
    console.log ("--unimplemented chain of responsibility actor.");
  }
}
export default Actor;
