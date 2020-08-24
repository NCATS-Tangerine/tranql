// source of following hsl related functions: https://stackoverflow.com/a/17433060

export function changeHue(rgb, degree) {
    var hsl = rgbToHSL(rgb);
    hsl.h += degree;
    if (hsl.h > 360) {
        hsl.h -= 360;
    }
    else if (hsl.h < 0) {
        hsl.h += 360;
    }
    return hslToRGB(hsl);
}

// expects a string and returns an object
export function rgbToHSL(rgb) {
    // strip the leading # if it's there
    rgb = rgb.replace(/^\s*#|\s*$/g, '');

    // convert 3 char codes --> 6, e.g. `E0F` --> `EE00FF`
    if(rgb.length === 3){
        rgb = rgb.replace(/(.)/g, '$1$1');
    }

    var r = parseInt(rgb.substr(0, 2), 16) / 255,
        g = parseInt(rgb.substr(2, 2), 16) / 255,
        b = parseInt(rgb.substr(4, 2), 16) / 255,
        cMax = Math.max(r, g, b),
        cMin = Math.min(r, g, b),
        delta = cMax - cMin,
        l = (cMax + cMin) / 2,
        h = 0,
        s = 0;

    if (delta === 0) {
        h = 0;
    }
    else if (cMax === r) {
        h = 60 * (((g - b) / delta) % 6);
    }
    else if (cMax === g) {
        h = 60 * (((b - r) / delta) + 2);
    }
    else {
        h = 60 * (((r - g) / delta) + 4);
    }

    if (delta === 0) {
        s = 0;
    }
    else {
        s = (delta/(1-Math.abs(2*l - 1)))
    }

    return {
        h: h,
        s: s,
        l: l
    }
}

// expects an object and returns a string
export function hslToRGB(hsl) {
    var h = hsl.h,
        s = hsl.s,
        l = hsl.l,
        c = (1 - Math.abs(2*l - 1)) * s,
        x = c * ( 1 - Math.abs((h / 60 ) % 2 - 1 )),
        m = l - c/ 2,
        r, g, b;

    if (h < 60) {
        r = c;
        g = x;
        b = 0;
    }
    else if (h < 120) {
        r = x;
        g = c;
        b = 0;
    }
    else if (h < 180) {
        r = 0;
        g = c;
        b = x;
    }
    else if (h < 240) {
        r = 0;
        g = x;
        b = c;
    }
    else if (h < 300) {
        r = x;
        g = 0;
        b = c;
    }
    else {
        r = c;
        g = 0;
        b = x;
    }

    r = normalize_rgb_value(r, m);
    g = normalize_rgb_value(g, m);
    b = normalize_rgb_value(b, m);

    return rgbToHex(r,g,b);
}

export function normalize_rgb_value(color, m) {
    color = Math.floor((color + m) * 255);
    if (color < 0) {
        color = 0;
    }
    return color;
}

export function rgbToHex(r, g, b) {
  r = Math.floor(r);
  g = Math.floor(g);
  b = Math.floor(b);
  return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

// Method for darkening the shade of a hex string
//    source: https://stackoverflow.com/questions/5560248/programmatically-lighten-or-darken-a-hex-color-or-rgb-and-blend-colors
export function shadeColor(color, percent) {
    //negative percent => darker

    var R = parseInt(color.substring(1,3),16);
    var G = parseInt(color.substring(3,5),16);
    var B = parseInt(color.substring(5,7),16);

    R = parseInt(R * (100 + percent) / 100);
    G = parseInt(G * (100 + percent) / 100);
    B = parseInt(B * (100 + percent) / 100);

    R = (R<255)?R:255;
    G = (G<255)?G:255;
    B = (B<255)?B:255;

    var RR = ((R.toString(16).length===1)?"0"+R.toString(16):R.toString(16));
    var GG = ((G.toString(16).length===1)?"0"+G.toString(16):G.toString(16));
    var BB = ((B.toString(16).length===1)?"0"+B.toString(16):B.toString(16));

    return "#"+RR+GG+BB;
}

/**
 * Adjust the title from camel case to title format (e.g "camel_case" => "Camel Case")
 *
 * @param {string} title - The string to be converted to title format
 *
 * @returns {string} - The string in title format
 */
export function adjustTitle(title) {
  // NOTE: This method of splitting by underscore will lead to adverse effects if types can have natural underscores in them
  // (Can they?)
  let newTitle = title.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  return newTitle;
}

/**
 * Groups Object[] into Object[][] based on accessor function (e.g. groupBy(list, (i) => [i.foo, i.bar]))
 * source: https://codereview.stackexchange.com/a/37132
 *
 */
export function groupBy( array , f ) {
  var groups = {};
  array.forEach( function( o )
  {
    var group = JSON.stringify( f(o) );
    groups[group] = groups[group] || [];
    groups[group].push( o );
  });
  return Object.keys(groups).map( function( group )
  {
    return groups[group];
  })
}

/**
 * Linear interpolation
 */
export function lerp(a, b, u) {
    return (1 - u) * a + u * b;
};


/**
 * Utility method to facilitate the debouncing of a function
 *
 * @param {function} func - Debounced function
 * @param {number} time - Amount of time in ms since the function's last attempted invocation required to pass for the function to actually be invoked
 * @private
 * @returns {function} - Debounced function that should be invoked rather than the actual one.
 */
export function debounce(func, time) {
  let timer;
  return function(...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(()=>func(...args), time);
  }
}

export function scrollIntoView(selector) {
  const element = document.querySelector(selector);
  element.scrollIntoView({
    block: 'start',
    behavior: 'smooth'
  });
}

/**
 * Restore component state from persistent storage on initialization.
 *
 */
export function hydrateState () {
  // for all items in state
  for (let key in this.state) {
    // if the key exists in localStorage
    if (localStorage.hasOwnProperty(key)) {
      // get the key's value from localStorage
      let value = localStorage.getItem(key);
      console.log (" setting " + key + " => " + value);
      // parse the localStorage string and setState
      const cb = () => console.log (" set " + key + " => " + this.state[key]);
      try {
        value = JSON.parse(value);
        this.setState({ [key]: value }, cb);
      } catch (e) {
        // handle empty string.
        console.log (" setting " + key + " => " + value);
        this.setState({ [key]: value }, cb);
      }
    }
  }
}

export function CSSStringtoRGB(string) {
  const colorNames = {
      aliceblue:'#f0f8ff', antiquewhite:'#faebd7', aqua:'#00ffff',
      aquamarine:'#7fffd4', azure:'#f0ffff', beige:'#f5f5dc',
      bisque:'#ffe4c4', black:'#000000', blanchedalmond:'#ffebcd',
      blue:'#0000ff', blueviolet:'#8a2be2', brown:'#a52a2a',
      burlywood:'#deb887', cadetblue:'#5f9ea0', chartreuse:'#7fff00',
      chocolate:'#d2691e', coral:'#ff7f50', cornflowerblue:'#6495ed',
      cornsilk:'#fff8dc', crimson:'#dc143c', cyan:'#00ffff',
      darkblue:'#00008b', darkcyan:'#008b8b', darkgoldenrod:'#b8860b',
      darkgray:'#a9a9a9', darkgreen:'#006400', darkkhaki:'#bdb76b',
      darkmagenta:'#8b008b', darkolivegreen:'#556b2f', darkorange:'#ff8c00',
      darkorchid:'#9932cc', darkred:'#8b0000', darksalmon:'#e9967a',
      darkseagreen:'#8fbc8f', darkslateblue:'#483d8b', darkslategray:'#2f4f4f',
      darkturquoise:'#00ced1', darkviolet:'#9400d3', deeppink:'#ff1493',
      deepskyblue:'#00bfff', dimgray:'#696969', dodgerblue:'#1e90ff',
      firebrick:'#b22222', floralwhite:'#fffaf0',
      forestgreen:'#228b22', fuchsia:'#ff00ff', gainsboro:'#dcdcdc',
      ghostwhite:'#f8f8ff', gold:'#ffd700', goldenrod:'#daa520', gray:'#808080',
      green:'#008000', greenyellow:'#adff2f', honeydew:'#f0fff0',
      hotpink:'#ff69b4', indianred:'#cd5c5c', indigo:'#4b0082',
      ivory:'#fffff0', khaki:'#f0e68c', lavender:'#e6e6fa',
      lavenderblush:'#fff0f5', lawngreen:'#7cfc00', lemonchiffon:'#fffacd',
      lightblue:'#add8e6', lightcoral:'#f08080', lightcyan:'#e0ffff',
      lightgoldenrodyellow:'#fafad2', lightgray:'#d3d3d3', lightgreen:'#90ee90',
      lightpink:'#ffb6c1', lightsalmon:'#ffa07a', lightseagreen:'#20b2aa',
      lightskyblue:'#87cefa', lightslategray:'#778899', lightsteelblue:'#b0c4de',
      lightyellow:'#ffffe0', lime:'#00ff00', limegreen:'#32cd32', linen:'#faf0e6',
      magenta:'#ff00ff', maroon:'#800000', mediumaquamarine:'#66cdaa',
      mediumblue:'#0000cd', mediumorchid:'#ba55d3', mediumpurple:'#9370db',
      mediumseagreen:'#3cb371', mediumslateblue:'#7b68ee',
      mediumspringgreen:'#00fa9a', mediumturquoise:'#48d1cc',
      mediumvioletred:'#c71585', midnightblue:'#191970', mintcream:'#f5fffa',
      mistyrose:'#ffe4e1', moccasin:'#ffe4b5', navajowhite:'#ffdead',
      navy:'#000080', oldlace:'#fdf5e6', olive:'#808000', olivedrab:'#6b8e23',
      orange:'#ffa500', orangered:'#ff4500', orchid:'#da70d6',
      alegoldenrod:'#eee8aa', palegreen:'#98fb98', paleturquoise:'#afeeee',
      palevioletred:'#db7093', papayawhip:'#ffefd5', peachpuff:'#ffdab9',
      peru:'#cd853f', pink:'#ffc0cb', plum:'#dda0dd', powderblue:'#b0e0e6',
      purple:'#800080', red:'#ff0000', rosybrown:'#bc8f8f', royalblue:'#4169e1',
      saddlebrown:'#8b4513', salmon:'#fa8072', sandybrown:'#f4a460',
      seagreen:'#2e8b57', seashell:'#fff5ee', sienna:'#a0522d',
      silver:'#c0c0c0', skyblue:'#87ceeb', slateblue:'#6a5acd',
      slategray:'#708090', snow:'#fffafa', springgreen:'#00ff7f',
      steelblue:'#4682b4', tan:'#d2b48c', teal:'#008080', thistle:'#d8bfd8',
      tomato:'#ff6347', turquoise:'#40e0d0', violet:'#ee82ee', wheat:'#f5deb3',
      white:'#ffffff', whitesmoke:'#f5f5f5', yellow:'#ffff00', yellowgreen:'#9acd32'
  };
  if (colorNames.hasOwnProperty(string)) {
    string = colorNames[string];
  }
  // Hex string shorthand
  let m = string.match(/^#([0-9a-f]{3})$/i);
  if (m) {
    m = m[1];
    return {
        r:parseInt(m.charAt(0),16)*0x11,
        g:parseInt(m.charAt(1),16)*0x11,
        b:parseInt(m.charAt(2),16)*0x11,
        a:1
    };
  }
  // Full hex string
  m = string.match(/^#([0-9a-f]{6})$/i);
  if (m) {
    m = m[1];
    return {
        r:parseInt(m.substr(0,2),16),
        g:parseInt(m.substr(2,2),16),
        b:parseInt(m.substr(4,2),16),
        a:1
    };
  }
  // RGB string
  m = string.match(/^rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
  if (m) {
      return {
        r:parseInt(m[1]),
        g:parseInt(m[2]),
        b:parseInt(m[3]),
        a:1
      };
  }
  m = string.match(/^rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*((\d+)?.*\d*)\s*\)$/i) || string.match(/^rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
  if (m) {
    return {
      r:parseInt(m[1]),
      g:parseInt(m[2]),
      b:parseInt(m[3]),
      a:parseFloat(m[4])
    };
  }

  console.warn(new Error(`Failed to parse CSS color string "${string}"`));
  return {
    r:255,
    g:255,
    b:255,
    a:1
  };
}

/**
 * Converts bytes to human-readable size string
 *    source: https://stackoverflow.com/a/18650828
 *
 * @param {Number} bytes - Number of bytes
 * @param {Number} [decimals=2] - Precision of result
 *
 * @returns {String} - Human readable result
 */
export function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0B';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + sizes[i];
}


/**
 * The following methods are for getting the cache size of the IndexedDB database
 *
 * Adapted from https://gist.github.com/tralves/9e5de2bd9f582007a52708d7d4209865
 */
export const getTableSize = function(db, dbName) {
 return new Promise((resolve,reject) => {
   if (db == null) {
     return reject();
   }
   var size = 0;
   var transaction = db.transaction([dbName])
     .objectStore(dbName)
     .openCursor();

   transaction.onsuccess = function(event){
       var cursor = event.target.result;
       if(cursor){
           var storedObject = cursor.value;
           var json = JSON.stringify(storedObject);
           size += json.length;
           cursor.continue();
       }
       else{
         resolve(size);
       }
   }.bind(this);
   transaction.onerror = function(err){
       reject("error in " + dbName + ": " + err);
   }
 });
}
/**
 * Returns object containing the sizes in bytes of each table in a given IndexedDB database
 *
 * @param {String} dbName - Name of the indexedDB database (in the Chrome you can go to `application->IndexedDB->${database_name}` to find a database's name)
 *
 * @returns {Promise<Object>} - A promise that resolves to an object whose entries are each table in the database and its respective size in bytes.
 */
export const getDatabaseSize = function (dbName) {
 return new Promise((resolve) => {
   var request = indexedDB.open(dbName);
   var db;
   var dbSize = 0;
   request.onerror = function(event) {
     // IndexedDB does not work/is disabled on this browser
     return {};
   };
   request.onsuccess = function(event) {
     db = event.target.result;
     var tableNames = [ ...db.objectStoreNames ];
     (function(tableNames, db) {
       var tableSizeGetters = tableNames
       .reduce( (acc, tableName) => {
         acc.push( getTableSize(db, tableName) );
         return acc;
       }, []);

       Promise.all(tableSizeGetters)
       .then(sizes => {
         const tableSizes = {};
         tableNames.forEach( (tableName,i) => {
           tableSizes[tableName] = sizes[i];
         });
         resolve(tableSizes);
       });
     })(tableNames, db);
   };
 });
}

/**
 * Object to query string
 * Source: https://stackoverflow.com/a/5505137
 */
export function toQueryString(obj) {
    var parts = [];
    for (var i in obj) {
        if (obj.hasOwnProperty(i)) {
            parts.push(encodeURIComponent(i) + "=" + encodeURIComponent(obj[i]));
        }
    }
    return parts.join("&");
}
