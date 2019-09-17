import React from 'react';
import ReactDOM from 'react-dom';

import App from './App';

window.bootstrap = (props) => ReactDOM.render(
  React.createElement(App, props),
  document.getElementById('root'));
