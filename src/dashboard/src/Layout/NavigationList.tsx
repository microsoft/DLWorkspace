import * as React from 'react'
import {
  FunctionComponent,
  forwardRef,
  useContext
} from 'react'

import {
  Link,
  LinkProps,
  matchPath,
  useLocation
} from 'react-router-dom'

import {
  Divider,
  List,
  ListItem,
  ListItemText
} from '@material-ui/core'

import ConfigContext from '../contexts/Config'

const ForwardedRefLink = forwardRef<Link, LinkProps>(
  (props, ref) => <Link ref={ref} {...props}/>
)

const ListItemLink: FunctionComponent<LinkProps> = (props) => {
  const { to } = props
  const location = useLocation()

  const locationPathname = location.pathname
  const toPathname = typeof to === "string"
    ? to
    : typeof to === "object"
      ? to.pathname
      : undefined

  const selected = typeof toPathname === "string"
    ? matchPath(locationPathname, toPathname) !== null
    : true

  return <ListItem button selected={selected} component={ForwardedRefLink} {...props}/>
}

const NavigationList: FunctionComponent = () => {
  const { wiki } = useContext(ConfigContext)
  return (
    <List component="nav" disablePadding>
      <ListItemLink to="/submission/training">
        <ListItemText>Submit Training Job</ListItemText>
      </ListItemLink>
      <ListItemLink to="/submission/data">
        <ListItemText>Submit Data Job</ListItemText>
      </ListItemLink>
      <ListItemLink to="/jobs">
        <ListItemText>View and Manage Jobs</ListItemText>
      </ListItemLink>
      <ListItemLink to="/jobs-legacy">
        <ListItemText secondary="(legacy)">View and Manage Jobs</ListItemText>
      </ListItemLink>
      <ListItemLink to="/clusters">
        <ListItemText>Cluster Status</ListItemText>
      </ListItemLink>
      <ListItemLink to="/cluster-status">
        <ListItemText secondary="(legacy)">Cluster Status</ListItemText>
      </ListItemLink>
      <Divider/>
      <ListItemLink to="/keys">
        <ListItemText>My SSH Keys</ListItemText>
      </ListItemLink>
      <ListItemLink to="/allowed-ip">
        <ListItemText>My Allowed IP</ListItemText>
      </ListItemLink>
      <Divider/>
      <ListItem button component="a" href={wiki} target="_blank" rel="noopener noreferrer">
        <ListItemText>DLTS Wiki</ListItemText>
      </ListItem>
    </List>
  )
}

export default NavigationList
