import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useContext,
  useState
} from 'react'

import {
  Button,
  makeStyles,
  createStyles
} from '@material-ui/core'
import {
  AccountBox
} from '@material-ui/icons'

import UserContext from '../../contexts/User'
import useUserDialog from '../../hooks/useUserDialog'

const useStyles = makeStyles(() => createStyles({
  'root': {
    whiteSpace: 'nowrap'
  }
}))

const UserButton: FunctionComponent = () => {
  const { givenName, familyName } = useContext(UserContext)
  const { open } = useUserDialog()
  const styles = useStyles()
  return (
    <Button
      variant="outlined"
      color="inherit"
      classes={styles}
      startIcon={<AccountBox/>}
      onClick={open}
    >
      {`${givenName} ${familyName}`}
    </Button>
  )
}

export default UserButton
