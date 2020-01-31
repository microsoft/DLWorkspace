import React from 'react';

import { BrowserRouter, Redirect, Route, RouteComponentProps, Switch } from "react-router-dom"

import 'typeface-roboto';
import 'typeface-roboto-mono';

import Helmet from 'react-helmet';
import { Box, CssBaseline, createMuiTheme, CircularProgress } from '@material-ui/core';
import { ThemeProvider } from "@material-ui/styles";
import { SnackbarProvider } from "notistack";

import ConfigContext, { Provider as ConfigProvider } from "./contexts/Config";
import UserContext, { Provider as UserProvider } from "./contexts/User";
import { Provider as ClustersProvider } from "./contexts/Clusters";
import { Provider as TeamProvider } from './contexts/Teams';

import { ConfirmProvider } from './hooks/useConfirm';

import AppBar from "./layout/AppBar";
import Content from "./layout/Content";
import Drawer from "./layout/Drawer";
import { Provider as DrawerProvider } from "./layout/Drawer/Context";

const Home = React.lazy(() => import('./pages/Home'));
const SignIn = React.lazy(() => import('./pages/SignIn'));
const Submission = React.lazy(() => import('./pages/Submission'));
const Jobs = React.lazy(() => import('./pages/Jobs'));
const JobsV2 = React.lazy(() => import('./pages/JobsV2'));
const Job = React.lazy(() => import('./pages/Job'));
const JobV2 = React.lazy(() => import('./pages/JobV2'));
const ClusterStatus = React.lazy( () => import('./pages/ClusterStatus'));

const theme = createMuiTheme();

interface BootstrapProps {
  config: ConfigContext;
  user: UserContext;
}

const Loading = (
  <Box flex={1} display="flex" alignItems="center" justifyContent="center">
    <CircularProgress/>
  </Box>
);

const Contexts: React.FC<BootstrapProps> = ({ config, user, children }) => {
  return (
    <BrowserRouter>
      <ConfigProvider {...config}>
        <UserProvider {...user}>
          <SnackbarProvider>
            <ConfirmProvider>
              <TeamProvider>
                <ClustersProvider>
                  <ThemeProvider theme={theme}>
                    {children}
                  </ThemeProvider>
                </ClustersProvider>
              </TeamProvider>
            </ConfirmProvider>
          </SnackbarProvider>
        </UserProvider>
      </ConfigProvider>
    </BrowserRouter>
  );
}

const Layout: React.FC<RouteComponentProps> = ({ location, history }) => {
  const { email } = React.useContext(UserContext);

  React.useEffect(() => {
    if (email === undefined) {
      history.replace({
        pathname: '/sign-in',
        state: { to: location.pathname }
      });
    }
  }, [email, history, location]);

  if (email === undefined) {
    return null;
  }

  return (
    <>
      <DrawerProvider>
        <Content>
          <AppBar/>
          <Drawer/>
          <React.Suspense fallback={Loading}>
            <Switch location={location}>
              <Route exact path="/" component={Home}/>
              <Route path="/submission" component={Submission}/>
              <Route path="/jobs/:cluster" component={Jobs}/>
              <Route path="/jobs" component={Jobs}/>
              <Route strict exact path="/jobs-v2/:clusterId/:jobId" component={JobV2}/>
              <Redirect strict exact from="/jobs-v2/:clusterId" to="/jobs-v2/:clusterId/"/>
              <Route strict exact path="/jobs-v2/:clusterId/" component={JobsV2}/>
              <Redirect strict exact from="/jobs-v2" to="/jobs-v2/"/>
              <Route strict exact path="/jobs-v2/" component={JobsV2}/>
              <Route path="/job/:team/:clusterId/:jobId" component={Job}/>
              <Route path="/cluster-status" component={ClusterStatus}/>
              <Redirect to="/"/>
            </Switch>
          </React.Suspense>
        </Content>
      </DrawerProvider>
    </>
  );
}

const App: React.FC<BootstrapProps> = (props) => (
    <Contexts {...props}>
      <Helmet
        titleTemplate="%s - Deep Learning Training Service"
        defaultTitle="Deep Learning Training Service"
      />
      <CssBaseline/>
      <Box display="flex" minHeight="100vh" maxWidth="100vw">
        <React.Suspense fallback={Loading}>
          <Switch>
            <Route exact path="/sign-in" component={SignIn}/>
            <Route component={Layout}/>
          </Switch>
        </React.Suspense>
      </Box>
    </Contexts>
);

export default App;
