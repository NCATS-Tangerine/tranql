import { Component } from 'react';
import Actor from "./Actor.js";

class Chain {
  constructor (chain=[]) {
    this._chain = chain;
  }
  add (actor) {
    this._chain.push (actor);
  }
  handle (message, context) {
    if (message) {
      for (var c = 0; c < this._chain.length; c++) {
        this._chain[c].handle (message, context);
      }
    }
    return message;
  }  
}

export default Chain;
