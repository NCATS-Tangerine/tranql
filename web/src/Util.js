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
    if(rgb.length == 3){
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

    if (delta == 0) {
        h = 0;
    }
    else if (cMax == r) {
        h = 60 * (((g - b) / delta) % 6);
    }
    else if (cMax == g) {
        h = 60 * (((b - r) / delta) + 2);
    }
    else {
        h = 60 * (((r - g) / delta) + 4);
    }

    if (delta == 0) {
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
 * @param {...<T>} varargs - Any additional arguments to pass to the function
 * @private
 * @returns {function} - Debounced function that should be invoked rather than the actual one.
 */
export function debounce(func, time, ...args) {
  let timer;
  return function() {
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
