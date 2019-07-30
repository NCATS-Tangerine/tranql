import { Component } from 'react';
import Dexie from 'dexie'
import dexieObservable from 'dexie-observable';
import { getDatabaseSize } from './Util.js';

class Cache extends Component {
  /**
   * A cache for the TranQL web app using the IndexedDB client DB.
   */
  constructor(props) {
    /* Create state elements and initialize configuration. */
    super(props);
    this.dbName = 'TranQLClientCache';
    this.db = new Dexie(this.dbName, { addons : [dexieObservable] });
    // Declare tables, IDs and indexes
    this.db.version(1).stores({
      cache: '++id, name, &key, graph',
      schema: '&id, graph'
    });

    // Dexie-observable adds some tracking tables to the database which we don't want to delete.
    this._trackingTables = ["_changes", "_syncNodes", "_intercomm", "_uncommittedChanges"];

    this.write = this.write.bind (this);

    this.getDatabaseSize = this.getDatabaseSize.bind(this);

    this.db.open();
  }
  async getDatabaseSize() {
    const tableSizes = Object.entries(await getDatabaseSize(this.dbName)).filter((table) => !this._trackingTables.includes(table[0])).map((table) => table[1]);
    const totalSize = tableSizes.reduce((acc,cur) => {
      acc += cur;
      return acc;
    },0);
    return totalSize;
  }
  async write (table, data) {
    // Write cache.

    // Iterate over all first-level keys in `data` and check if they are a unique key in `table`'s schema.
    // If so (there will always be at least one present if the table has at least one unique key), check to
    // see if there are any existing entries with an identical value in said unique key.
    // If so, we have to update the entry (we can't replace it).
    const prop = Object.keys(data)
      .filter((key) => [this.db[table].schema.primKey,...this.db[table].schema.indexes]
        .filter((index) => index.unique && index.name === key).length > 0
      )[0];
    // This will update the entry if an entry already exists containing a duplicate unique key as `data`
    if ((await this.read(table, prop, data[prop])).length > 0) {
      return await this.db[table].where(prop).equals(data[prop]).modify(data);
    }
    else {
      return await this.db[table].put (data);
    }

  }
  async read (table, prop, key) {
    return await this.db[table]
    .where(prop)
    .equals (key)
    .toArray();
  }
  async get (table, id, callback) {
    return await this.db[table].get (id, callback);
  }
  async clear () {
    const tables = this.db.tables.filter((table) => !this._trackingTables.includes(table.name));
    return await tables.forEach((table) => table.clear ());
  }
}

export default Cache;
