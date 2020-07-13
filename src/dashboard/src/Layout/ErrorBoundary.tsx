import * as React from 'react'
import {
  Component,
  ComponentType,
  ErrorInfo,
  FunctionComponent,
  ReactElement,
  useCallback,
  useContext,
  useMemo
} from 'react'

import {
  Box,
  Typography,
  Link
} from '@material-ui/core'
import {
  Error
} from '@material-ui/icons'

import ConfigContext from '../contexts/Config'

const ErrorBox: FunctionComponent = () => {
  const { support } = useContext(ConfigContext)

  const contactHref = useMemo(() => {
    const subject = 'DLTS dashboard crash'
    const body = `
Hi DLTS support team,

I found a DLTS dashboard crash on ${window.location.href} . Below is what I did:

1. ...
2. ...
    `.trim()
    return `mailto:${support !== undefined ? support : ''}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  }, [support])

  const handleRefresh = useCallback(() => {
    window.location.reload(true)
  }, [])

  return (
    <Box alignItems="center">
      <Error fontSize="large" color="error"/>
      <Typography variant="h3" component="h1">
        DLTS Cannot Show What You Want
        <span role="img" aria-label="(sad)">☹️</span>
      </Typography>
      <Typography variant="body1">
        Try the following steps:
        <ol>
          <li><Link onClick={handleRefresh}>Refresh</Link> the page.</li>
          <li><Link href="/api/authenticate/logout">Sign out</Link> and sign in.</li>
          <li><Link href={contactHref}>Contact</Link> the support team.</li>
        </ol>
      </Typography>
    </Box>
  )
}

interface Props { children: ReactElement }
interface State { isError: boolean }

class ProductionErrorBoundary extends Component<Props, State> {
  constructor (props: Props) {
    super(props)
    this.state = { isError: false }
  }

  static getDerivedStateFromError () {
    return { isError: true }
  }

  componentDidCatch (error: Error, errorInfo: ErrorInfo) {
    const image = new Image()
    const queries = []
    queries.push(`message=${encodeURIComponent(error.message)}`)
    queries.push(`source=${encodeURIComponent(errorInfo.componentStack)}`)
    image.src = `/api/error.gif?${queries.join('&')}`

    console.error(error)
    console.error(errorInfo)
  }

  render () {
    const { children } = this.props
    const { isError } = this.state
    if (isError) {
      return <ErrorBox/>
    }
    return children
  }
}

const DevelopmentErrorBoundary: FunctionComponent<Props> = ({ children }) => {
  return children
}

const ErrorBoundary: ComponentType<Props> =
  process.env.NODE_ENV === 'production'
    ? ProductionErrorBoundary
    : DevelopmentErrorBoundary

export default ErrorBoundary
