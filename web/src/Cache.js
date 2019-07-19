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
      console.log("UPDATE",prop,data);
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
    return await this.db.tables.forEach((table) => table.clear ());
  }
}

export default Cache;
