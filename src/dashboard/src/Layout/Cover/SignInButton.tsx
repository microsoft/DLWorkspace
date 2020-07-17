import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useState
} from 'react'

import {
  Button,
  CircularProgress
} from '@material-ui/core'

const SignInButton: FunctionComponent = () => {
  const [busy, setBusy] = useState(false)

  const getHref = useCallback(() => {
    const to = window.location.pathname +
      window.location.search +
      window.location.hash

    if (to === '/') {
      return '/api/authenticate'
    } else {
      return '/api/authenticate?to=' + encodeURIComponent(to)
    }
  }, [])

  const handleClick = useCallback(() => {
    setBusy(true)
  }, [setBusy])

  return (
    <Button
      variant="outlined"
      color="primary"
      href={getHref()}
      disabled={busy}
      onClick={handleClick}
    >
      { busy && <CircularProgress size={24}/> }
      { !busy && 'Sign in with corp account' }
    </Button>
  )
}

export default SignInButton
