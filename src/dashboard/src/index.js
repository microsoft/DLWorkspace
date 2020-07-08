import * as React from 'react'
import * as ReactDOM from 'react-dom'

import App from './App'

window.bootstrap = (props) => ReactDOM.render(
  React.createElement(App, props),
  document.getElementById('root'))

window.onerror = (message, source, line, col, error) => {
  const image = new Image()
  const queries = []
  queries.push(`message=${encodeURIComponent(message)}`)
  queries.push(`source=${encodeURIComponent(source)}`)
  queries.push(`line=${encodeURIComponent(line)}`)
  queries.push(`col=${encodeURIComponent(col)}`)
  if (error && error.stack) {
    queries.push(`stack=${encodeURIComponent(error.stack)}`)
  }
  image.src = `/api/error.gif?${queries.join('&')}`
}
