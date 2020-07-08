import * as React from 'react'
import {
  FunctionComponent,
  useContext
} from 'react'

import {
  Box,
  CircularProgress,
  Divider,
  IconButton,
  ListItem,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText
} from '@material-ui/core'
import {
  SvgIconComponent,
  Settings
} from '@material-ui/icons'

import Context from './Context'

interface SettingItemProps {
  Icon: SvgIconComponent
  name: string
  text: string | undefined
  onConfigure(): void
}

const SettingItem: FunctionComponent<SettingItemProps> = ({ Icon, name, text, onConfigure }) => {
  const { admin } = useContext(Context)
  return (
    <ListItem>
      <ListItemIcon>
        <Icon/>
      </ListItemIcon>
      <ListItemText primary={name} secondary={text}/>
      { text === undefined && (
        <ListItemSecondaryAction>
          <CircularProgress size={24}/>
        </ListItemSecondaryAction>
      ) }
      { text !== undefined && admin && (
        <ListItemSecondaryAction>
          <Box display="flex">
            <Divider orientation="vertical" flexItem/>
            <Box marginRight={2}/>
            <IconButton onClick={onConfigure}>
              <Settings/>
            </IconButton>
          </Box>
        </ListItemSecondaryAction>
      ) }
    </ListItem>
  )
}

export default SettingItem
