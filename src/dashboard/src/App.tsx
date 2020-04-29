import React from 'react';

import { BrowserRouter, Redirect, Route, RouteComponentProps, Switch } from "react-router-dom"

import 'typeface-roboto';
import 'typeface-roboto-mono';

import Helmet from 'react-helmet';
import { Typography } from '@material-ui/core';
import { Box, CssBaseline, createMuiTheme } from '@material-ui/core';
import { ThemeProvider } from "@material-ui/styles";
import { SnackbarProvider } from "notistack";
import {
  Provider as UseHttpProvider,
  Options as UseHttpOptions,
  CachePolicies,
} from "use-http-2";

import Loading from './components/Loading';

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
const JobsLegacy = React.lazy(() => import('./pages/JobsLegacy'));
const Job = React.lazy(() => import('./pages/Job'));
const JobLegacy = React.lazy(() => import('./pages/JobLegacy'));
const ClusterStatus = React.lazy( () => import('./pages/ClusterStatus'));
const Clusters = React.lazy(() => import('./pages/Clusters'));
const Cluster = React.lazy(() => import('./pages/Cluster'));

const theme = createMuiTheme();
const useHttpOptions: UseHttpOptions = {
  cachePolicy: CachePolicies.NO_CACHE
};

interface BootstrapProps {
  config: ConfigContext;
  user: UserContext;
}

const PageLoading = (
  <Box
    flex={1}
    display="flex"
    flexDirection="column"
    justifyContent="center"
    alignItems="center"
  >
    <Loading/>
    <Typography component="p" variant="subtitle1">Loading Page</Typography>
  </Box>
);

const Contexts: React.FC<BootstrapProps> = ({ config, user, children }) => {
  return (
    <BrowserRouter>
      <UseHttpProvider options={useHttpOptions}>
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
      </UseHttpProvider>
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
          <React.Suspense fallback={PageLoading}>
            <Switch location={location}>
              <Route exact path="/" component={Home}/>

              <Route path="/submission" component={Submission}/>

              <Route strict exact path="/jobs/:clusterId/:jobId" component={Job}/>
              <Redirect strict exact from="/jobs/:clusterId" to="/jobs/:clusterId/"/>
              <Route strict exact path="/jobs/:clusterId/" component={Jobs}/>
              <Redirect strict exact from="/jobs" to="/jobs/"/>
              <Route strict exact path="/jobs/" component={Jobs}/>

              <Route path="/jobs-legacy/:cluster" component={JobsLegacy}/>
              <Route path="/jobs-legacy" component={JobsLegacy}/>
              <Route path="/job-legacy/:team/:clusterId/:jobId" component={JobLegacy}/>

              <Redirect strict exact from="/clusters" to="/clusters/"/>
              <Route strict exact path="/clusters/" component={Clusters}/>
              <Route strict exact path="/clusters/:clusterId" component={Cluster}/>

              <Route path="/cluster-status" component={ClusterStatus}/>

              {/* Backward Compatibility Routes */}
              <Route strict exact path="/jobs-v2:rest(.*)"
                render={({ match }) => <Redirect to={`/jobs${match.params['rest']}`}/>}
              />
              <Redirect path="/job/:team/:clusterId/:jobId" to="/jobs/:clusterId/:jobId"/>

              {/* 404 */}
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
