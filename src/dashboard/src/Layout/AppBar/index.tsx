import * as React from 'react'
import { FunctionComponent } from 'react'

import {
  AppBar as UIAppBar,
  Grid,
  Toolbar,
  Hidden
} from '@material-ui/core'
import { createStyles, makeStyles } from '@material-ui/core/styles'
import ToggleDrawerButton from './ToggleDrawerButton'
import Brand from './Brand'
import TeamMenuButton from './TeamMenuButton'
import UserButton from './UserButton'
import SignOutButton from './SignOutButton'

const useAppBarStyles = makeStyles(theme => createStyles({
  root: {
    zIndex: theme.zIndex.drawer + 1
  }
}))

const AppBar: FunctionComponent = () => {
  const appBarStyles = useAppBarStyles()
  return (
    <UIAppBar position="fixed" classes={appBarStyles}>
      <Toolbar>
        <Grid container wrap="nowrap" justify="flex-end" alignItems="center" spacing={1}>
          <Grid item>
            <ToggleDrawerButton/>
          </Grid>
          <Grid item xs>
            <Hidden xsDown>
              <Brand/>
            </Hidden>
          </Grid>
          <Grid item>
            <TeamMenuButton/>
          </Grid>
          <Grid item>
            <UserButton/>
          </Grid>
          <Grid item>
            <SignOutButton/>
          </Grid>
        </Grid>
      </Toolbar>
    </UIAppBar>
  )
}

export default AppBar
