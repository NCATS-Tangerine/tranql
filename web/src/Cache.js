import { Component } from 'react';
import Dexie from 'dexie'

class Cache extends Component {
  /**
   * A cache for the TranQL web app using the IndexedDB client DB.
   */
  constructor(props) {
    /* Create state elements and initialize configuration. */
    super(props);
    this.db = new Dexie('TranQLClientCache');
    // Declare tables, IDs and indexes
    this.db.version(1).stores({
      cache: '++id, name, &key, graph',
      schema: '&id, graph'
    });
    this.write = this.write.bind (this);
  }
  async write (table, data) {
    // Write cache.
    return await this.db[table].put (data);
  }
  async read (table, key) {
    return await this.db[table]
    .where('key')
    .equals (key)
    .toArray();
  }
  async get (table, id, callback) {
    return await this.db[table].get (id, callback);
  }
  async clear () {
    return await this.db.tables.forEach((table) => table.clear ());
  }
}

export default Cache;
