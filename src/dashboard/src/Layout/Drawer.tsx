import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect
} from 'react';

import {
  Drawer as UIDrawer,
  Theme,
  createStyles,
  makeStyles,
  useMediaQuery,
  useTheme,
  Toolbar
} from '@material-ui/core';

import LayoutContext from './Context';

const useStyles = makeStyles((theme: Theme) => createStyles({
  paper: {
    width: theme.spacing(30)
  }
}));

const Drawer: FunctionComponent = ({ children }) => {
  const { drawerOpen, setDrawerOpen } = useContext(LayoutContext);
  const onClose = useCallback(() => setDrawerOpen(false), [setDrawerOpen]);
  const theme = useTheme();
  const styles = useStyles();
  const isDesktop = useMediaQuery(theme.breakpoints.up("sm"));
  const variant = isDesktop ? "persistent" : "temporary";

  useEffect(() => {
    if (isDesktop) { setDrawerOpen(true); }
  }, [isDesktop, setDrawerOpen]);

  return (
    <UIDrawer
      variant={variant}
      open={drawerOpen}
      onClose={onClose}
      classes={styles}
    >
      <Toolbar disableGutters/>
      {children}
    </UIDrawer>
  );
};

export default Drawer;
