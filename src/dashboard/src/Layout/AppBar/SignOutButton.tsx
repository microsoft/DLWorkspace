import * as React from 'react'
import {
  FunctionComponent
} from 'react'

import {
  IconButton,
  Tooltip
} from '@material-ui/core'
import {
  ExitToApp
} from '@material-ui/icons'

const SignOutButton: FunctionComponent = () => {
  return (
    <Tooltip title="Sign Out">
      <IconButton edge="end" color="inherit" href="/api/authenticate/logout">
        <ExitToApp />
      </IconButton>
    </Tooltip>
  )
}

export default SignOutButton
