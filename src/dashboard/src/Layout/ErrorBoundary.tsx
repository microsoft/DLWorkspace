import * as React from 'react'
import {
  Component,
  ErrorInfo,
  FunctionComponent,
  ReactNode,
  useCallback,
  useContext,
  useMemo
} from 'react'

import {
  Box,
  Container,
  Typography,
  Link
} from '@material-ui/core'
import {
  MoodBad
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
    <Container>
      <Box display="flex" flexDirection="column" alignItems="center">
        <Typography variant="h1" component="div">
          <MoodBad fontSize="inherit"/>
        </Typography>
        <Typography variant="h4" component="h1">
          Cannot show the page...
        </Typography>
        <Box marginTop={5}>
          <Typography>
            <strong>Try:</strong>
            <Box component="ul" marginTop={0}>
              <li>
                <Link variant="body1" underline="always" component="button" onClick={handleRefresh}>
                  Full Refresh
                </Link>
              </li>
              <li>
                <Link href="/api/authenticate/logout" variant="body1" underline="always">
                  Sign out and sign in
                </Link>
              </li>
              <li>
                <Link href={contactHref} variant="body1" underline="always">
                  Contact the support team
                </Link>
              </li>
            </Box>
          </Typography>
        </Box>
      </Box>
    </Container>
  )
}

interface Props { children: ReactNode }
interface State { isError: boolean }

class ErrorBoundary extends Component<Props, State> {
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

export default ErrorBoundary
