import * as React from 'react'
import {
  FunctionComponent,
  useContext
} from 'react'

import {
  Box,
  Toolbar,
  createStyles,
  makeStyles
} from '@material-ui/core'

import LayoutContext from './Context'
import NotificationBox from './NotificationBox'

const useStyles = makeStyles(theme => createStyles({
  root: ({ drawerOpen }: { drawerOpen: boolean }) => ({
    marginLeft: drawerOpen ? theme.spacing(30) : 0,
    transition: theme.transitions.create('margin-left', {
      easing: theme.transitions.easing.easeInOut,
      duration: drawerOpen
        ? theme.transitions.duration.enteringScreen
        : theme.transitions.duration.leavingScreen
    })
  })
}))

const Content: FunctionComponent = ({ children }) => {
  const { drawerOpen } = useContext(LayoutContext)

  const styles = useStyles({ drawerOpen })

  return (
    <Box flex={1} py={3} className={styles.root}>
      <Toolbar disableGutters/>
      <NotificationBox marginTop={-3} marginBottom={3}/>
      {children}
    </Box>
  )
}

export default Content
