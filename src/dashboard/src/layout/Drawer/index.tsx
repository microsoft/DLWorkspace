import React from "react";
import { Link, LinkProps, matchPath, RouteComponentProps, withRouter } from "react-router-dom";
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
import Context from "./Context";


const useStyles = makeStyles((theme: Theme) => createStyles({
  title: {
    padding: theme.spacing(1)
  },
  titleLink: {
    textDecoration: "none"
  },
  drawerHeader: {
    marginTop:64,
    display: 'flex',
    flexDirection:'column',
    alignItems: 'center',
    padding: '0 8px',
    ...theme.mixins.toolbar,
    justifyContent: 'flex-end',
  },
}));

export const ListLink = React.forwardRef<Link, LinkProps>(
  ({ to, ...props }, ref) => <Link ref={ref} to={to} {...props}/>
);

const LinkListItem = withRouter<LinkProps & RouteComponentProps>(({ location, to, children }) => {
  const locationPathname = location.pathname;
  const toPathname = typeof to === "string" ? to : to.pathname;
  const selected = typeof toPathname === "string"
    ? matchPath(locationPathname, toPathname) !== null
    : true;
  return (
    <ListItem button selected={selected} component={ListLink} to={to}>
      {children}
    </ListItem>
  );
});

const NavigationList: React.FC = () => {
  const styles = useStyles();
  return (
    <List component="nav" className={styles.drawerHeader}>
      <LinkListItem to="/submission/training">
        <ListItemText>Submit Training Job</ListItemText>
      </LinkListItem>
      <LinkListItem to="/submission/data">
        <ListItemText>Submit Data Job</ListItemText>
      </LinkListItem>
      <LinkListItem to="/jobs">
        <ListItemText>View and Manage Jobs</ListItemText>
      </LinkListItem>
      <LinkListItem to="/cluster-status">
        <ListItemText>Cluster Status</ListItemText>
      </LinkListItem>
    </List>
  );
};

const DashboardDrawer: React.FC = () => {
  const { open, setOpen } = React.useContext(Context);
  const onClose = React.useCallback(() => setOpen(false), [setOpen]);
  const theme = useTheme();
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
    >
      <Divider/>
      <NavigationList />
    </Drawer>
  );
};

export default DashboardDrawer;
