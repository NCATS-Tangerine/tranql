import * as THREE from 'three';
import { lerp, rgbToHex } from './Util.js';
/**
 * Messy rewrite that was so long that it had to be in its own file.
 * DO NOT USE. This method has not been written to be used alone. You should use App::_highlightType which calls this method bound to the App internally.
 */
export default function highlightTypes(elements, type, highlight, outline, fade) {
  const vMode = this.state.visMode;
  if (fade.duration > 0) {
    if (elements.length === 0) {
      return Promise.resolve(undefined);
    }
    let id = type;
    if (typeof this._highlightTypeFadeIntervals[id] === "undefined") {
      this._highlightTypeFadeIntervals[id] = {};
    }
    if (typeof this._highlightTypeFadeIntervals[id].timeout !== "undefined") {
      // console.log('clear');
      clearInterval(this._highlightTypeFadeIntervals[id].timeout);
      clearInterval(this._highlightTypeFadeIntervals[id].interval);
      delete this._highlightTypeFadeIntervals[id].timeout;
      delete this._highlightTypeFadeIntervals[id].interval;
    }
    for (let i=0;i<elements.length;i++) {
      let element = elements[i];
      let graphElementType = element.graphElementType;
      element = element.element;
      if (highlight !== false) {
        if (vMode === "2D") {
          element.prevColor = element.color;
        }
      }
    }
    // Previous block is to set prevColor so that it functions correctly with 2D
    let timeoutPromise = new Promise((resolveTimeout) => {
      let theTimeout = setTimeout(() => {
        if (typeof this._highlightTypeFadeIntervals[id].interval !== "undefined") {
          // console.log('clear');
          clearInterval(this._highlightTypeFadeIntervals[id].interval);
          delete this._highlightTypeFadeIntervals[id].interval;
        }
        let intervalPromise = new Promise((resolveInterval) => {
          const duration = fade.duration;
          let interval = 15;
          let steps = duration / interval;
          let step_u = 1.0 / steps;
          let u = 0.0;

          for (let i=0;i<elements.length;i++) {
            let element = elements[i];
            if (vMode === "2D") {
              element.start = {
                r: parseInt(element.element.color.substr(1, 2), 16) / 255,
                g: parseInt(element.element.color.substr(3, 2), 16) / 255,
                b: parseInt(element.element.color.substr(5, 2), 16) / 255,
              };
            }
            else {
              let mat = (element.element.__lineObj || element.element.__threeObj).material;
              element.start = {
                r:mat.color.r,
                g:mat.color.g,
                b:mat.color.b
              };
            }
            let color;
            let opacity;
            if (highlight !== false) {
              color = new THREE.Color(highlight);
            }
            else {
              if (vMode !== "2D") {
                color = new THREE.Color(parseInt(element.element.color.slice(1),16));
              }
              else {
                color = new THREE.Color(parseInt(element.element.prevColor.slice(1),16));
              }
            }
            element.end = {
              r:color.r,
              g:color.g,
              b:color.b
            };
          }

          // Slightly modified code from https://stackoverflow.com/a/11293378
          let theInterval = setInterval(() => {
            for (let i=0;i<elements.length;i++) {
              let element = elements[i];
              let r = lerp(element.start.r, element.end.r, u);
              let g = lerp(element.start.g, element.end.g, u);
              let b = lerp(element.start.b, element.end.b, u);
              let graphElementType = element.graphElementType;
              element = element.element;
              let obj = (element.__lineObj || element.__threeObj); //THREE.Mesh;
              let material;
              if (vMode !== "2D") {
                if (obj === undefined) continue;
                material = obj.material; // : THREE.MeshLambertMaterial
              }
              if (u >= 1.0) {
                if (vMode === "2D") {
                  element.color = rgbToHex(element.end.r*255,element.end.g*255,element.end.b*255);
                }
                else {
                  material.color = new THREE.Color(element.end.r,element.end.g,element.end.b);
                }
                // if (opacity !== undefined) material.opacity = opacity;
              }
              if (vMode === "2D") {
                element.color = rgbToHex(r*255,g*255,b*255);
              }
              else {
                material.color = new THREE.Color(r,g,b);
                // if (opacity !== undefined) material.opacity = opacity;
              }
            }
            u += step_u;
            if (u >= 1.0) {
              clearInterval(theInterval);
              resolveInterval();
            }
          }, interval);
          this._highlightTypeFadeIntervals[id].interval = theInterval;
        });
        resolveTimeout(intervalPromise);
      }, fade.offset);
      this._highlightTypeFadeIntervals[id].timeout = theTimeout;
    });
    return timeoutPromise;
  }
  else {
    for (let i=0;i<elements.length;i++) {
      let element = elements[i];
      let graphElementType = element.graphElementType;
      element = element.element;
      let obj = (element.__lineObj || element.__threeObj); //THREE.Mesh;
      let material;
      if (vMode !== "2D") {
        if (obj === undefined) return;
        material = obj.material; // : THREE.MeshLambertMaterial
      }
      let color;
      let opacity;
      if (highlight !== false) {
        color = new THREE.Color(highlight);
        if (vMode !== "2D") {
          element.prevOpacity = material.opacity;
        }
        else {
          element.prevColor = element.color;
        }
        opacity = 1;
      }
      else {
        if (vMode !== "2D") {
          color = new THREE.Color(parseInt(element.color.slice(1),16));
          opacity = element.prevOpacity;
          delete element.prevOpacity;
        }
        else {
          color = new THREE.Color(parseInt(element.prevColor.slice(1),16));
          // delete element.color;
        }
      }
      if (vMode === "2D") {
        element.color = "#" + color.getHexString();
      }
      else {
        material.color = color;
        material.opacity = opacity;
      }
    }
  }
}
