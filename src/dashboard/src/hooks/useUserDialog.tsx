import * as React from 'react'

import {
  FunctionComponent,
  createContext,
  useCallback,
  useContext,
  useState
} from 'react'

import {
  Dialog,
  DialogTitle,
  Divider,
  Link,
  List,
  ListItem,
  ListItemText
} from '@material-ui/core'

import UserContext from '../contexts/User'
import TeamContext from '../contexts/Team'

const Context = createContext({ open: () => {} })

export const UserDialogProvider: FunctionComponent = ({ children }) => {
  const { email, password } = useContext(UserContext)
  const { currentTeamId } = useContext(TeamContext)
  const api = window.location.origin + `/api/teams/${currentTeamId}/jobs` +
    `?email=${encodeURIComponent(email || '')}&password=${encodeURIComponent(password || '')}`
  const [open, setOpen] = useState(false)
  const handleOpen = useCallback(() => {
    setOpen(true)
  }, [])
  const handleClose = useCallback(() => {
    setOpen(false)
  }, [])

  return (
    <Context.Provider value={{ open: handleOpen }}>
      {children}
      <Dialog
        maxWidth={false}
        open={open}
        onClose={handleClose}
      >
        <DialogTitle>User Account</DialogTitle>
        <Divider/>
        <List dense disablePadding>
          <ListItem>
            <ListItemText primary="Email" secondary={email}/>
          </ListItem>
          <ListItem>
            <ListItemText primary="Password" secondary={password}/>
          </ListItem>
          <Divider/>
          <ListItem>
            <ListItemText
              primary="Try an API"
              secondary={api}
              secondaryTypographyProps={{
                component: Link,
                href: api,
                target: '_blank',
                rel: 'noopener noreferrer'
              }}
            />
          </ListItem>
        </List>
      </Dialog>
    </Context.Provider>
  )
}

export default function useUserDialog () {
  return useContext(Context)
}
