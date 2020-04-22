import React from "react";
import { Link, LinkProps, matchPath, useLocation } from "react-router-dom";

import {
  Drawer,
  Theme,
  List,
  ListItem,
  ListItemText,
  Divider,
  useMediaQuery
} from "@material-ui/core";
import {
  useTheme,
} from "@material-ui/core/styles";
import { makeStyles, createStyles } from "@material-ui/core/styles";
import Context, { WIDTH } from "./Context";
import ConfigContext from "../../contexts/Config";

const useNavigationListStyles = makeStyles((theme: Theme) => createStyles({
  root: {
    marginTop: 64,
    display: 'flex',
    flexDirection:'column',
    alignItems: 'center',
    padding: '0 8px',
    ...theme.mixins.toolbar,
    justifyContent: 'flex-end',
  },
}));

const useDashboardDrawerStyles = makeStyles({
  paper: {
    width: WIDTH
  }
});

export const ListLink = React.forwardRef<Link, LinkProps>(
  ({ to, ...props }, ref) => <Link ref={ref} to={to} {...props}/>
);

const LinkListItem: React.FC<LinkProps> = ({ to, children }) => {
  const location = useLocation();

  const locationPathname = location.pathname;
  const toPathname = typeof to === "string" ? to
    : typeof to === "object" ? to.pathname
      : undefined;
  const selected = typeof toPathname === "string"
    ? matchPath(locationPathname, toPathname) !== null
    : true;
  return (
    <ListItem button selected={selected} component={ListLink} to={to}>
      {children}
    </ListItem>
  );
};

const NavigationList: React.FC = () => {
  const styles = useNavigationListStyles();
  const { wiki } = React.useContext(ConfigContext);
  return (
    <List component="nav" classes={styles}>
      <LinkListItem to="/submission/training">
        <ListItemText>Submit Training Job</ListItemText>
      </LinkListItem>
      <LinkListItem to="/submission/data">
        <ListItemText>Submit Data Job</ListItemText>
      </LinkListItem>
      <LinkListItem to="/jobs">
        <ListItemText>View and Manage Jobs</ListItemText>
      </LinkListItem>
      <LinkListItem to="/jobs-v2">
        <ListItemText>View and Manage Jobs V2</ListItemText>
      </LinkListItem>
      <LinkListItem to="/cluster-status">
        <ListItemText>Cluster Status</ListItemText>
      </LinkListItem>
      <LinkListItem to="/clusters">
        <ListItemText>Cluster Status V2</ListItemText>
      </LinkListItem>
      <ListItem button>
        <ListItemText>
          <a href={wiki} target="_blank" style={{ textDecoration:'none' }}>DLTS Wiki</a>
        </ListItemText>
      </ListItem>
    </List>
  );
};

const DashboardDrawer: React.FC = () => {
  const { open, setOpen } = React.useContext(Context);
  const onClose = React.useCallback(() => setOpen(false), [setOpen]);
  const theme = useTheme();
  const styles = useDashboardDrawerStyles();
  const isDesktop = useMediaQuery(theme.breakpoints.up("sm"));
  const variant = isDesktop ? "persistent" : "temporary";

  React.useEffect(() => {
    if (isDesktop) { setOpen(true); }
  }, [isDesktop, setOpen]);
  return (
    <Drawer
      variant={variant}
      open={open}
      onClose={onClose}
      classes={styles}
    >
      <Divider/>
      <NavigationList />
    </Drawer>
  );
};

export default DashboardDrawer;
