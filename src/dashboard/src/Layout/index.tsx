import * as React from 'react';
import {
  FunctionComponent,
  useContext,
} from 'react';

import { Box, CircularProgress } from '@material-ui/core';

import UserContext from '../contexts/User';
import TeamsContext from '../contexts/Teams';

import AppBar from './AppBar';
import Content from './Content';
import { LayoutProvider } from './Context';
import Cover from './Cover';
import SignInButton from './Cover/SignInButton';
import UnauthorizedDialog from './Cover/UnauthorizedDialog';
import Drawer from './Drawer';
import NavigationList from './NavigationList';

const LayoutContent: FunctionComponent = ({ children }) => {
  const { email } = useContext(UserContext);
  const { teams } = useContext(TeamsContext);

  if (email == null) {
    return (
      <Cover>
        <SignInButton/>
      </Cover>
    );
  }

  if (teams == null) {
    return (
      <Cover>
        <CircularProgress/>
      </Cover>
    );
  }
  if (teams.length === 0) {
    return (
      <Cover>
        <UnauthorizedDialog/>
      </Cover>
    );
  }

  return (
    <LayoutProvider>
      <AppBar/>
      <Drawer>
        <NavigationList/>
      </Drawer>
      <Content>
        {children}
      </Content>
    </LayoutProvider>
  );
};

const Layout: FunctionComponent = ({ children }) => (
  <Box width="100vw" minHeight="100vh" display="flex">
    <LayoutContent>
      {children}
    </LayoutContent>
  </Box>
);

export default Layout;
