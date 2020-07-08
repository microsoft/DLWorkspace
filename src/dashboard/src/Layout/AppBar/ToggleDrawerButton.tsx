import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useContext
} from "react"

import {
  IconButton,
  Tooltip
} from '@material-ui/core'
import {
  Menu
} from '@material-ui/icons'

import LayoutContext from '../Context'

const ToggleDrawerButton: FunctionComponent = () => {
  const { setDrawerOpen } = useContext(LayoutContext)
  const handleClick = useCallback(() => setDrawerOpen(drawerOpen => !drawerOpen), [setDrawerOpen])
  return (
    <Tooltip title="Toggle Sidebar">
      <IconButton edge="start" color="inherit" onClick={handleClick}>
        <Menu/>
      </IconButton>
    </Tooltip>
  )
}

export default ToggleDrawerButton
