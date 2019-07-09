import React from 'react';
import { confirmAlert as nativeConfirmAlert } from 'react-confirm-alert';
import { Button } from 'reactstrap'
import './confirmAlert.css';
/**
 * Creates a uniform appearance app-wide without having to use the same custom UI every time.
 * Basic use is identical to the native function. Args.other allows for more specific customization.
 *
 * @param {Object} args - Slightly modified version of the native confirmAlert function's arguments
 * @param {String} args.title - Title contained within an h3 element.
 * @param {String} args.message - The body of the alert message.
 * @param {Object[]} args.buttons - The buttons within the confirmAlert. Structured as {`label`: String, `onClick`: Function, `props`: Object[]}
 *    The props property will allow for the overriding of the default props that the buttons have (e.g. {color: 'secondary'}).
 * @param {Object[]} args.other - Any other options to pass directly to the native function (e.g. {closeOnEscape: true}).
 */
export default function confirmAlert(args) {
  return nativeConfirmAlert({
    customUI: ({ onClose }) => (
      <div className="confirm-alert">
       <h3>{args.title}</h3>
       <p>{args.message}</p>
       {
         args.buttons.map((button,i) => (
           <Button key={i} color="primary" onClick={() => {
             onClose();
             button.onClick();
           }} {...button.props}>{button.label}</Button>
         ))
       }
      </div>
    ),
    ...args.other
  });
}
