import React, {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react';
import Helmet from 'react-helmet';
import { Link as RouterLink } from 'react-router-dom';

import {
  Breadcrumbs,
  Container,
  Hidden,
  Link as UILink,
  Paper,
  Tabs,
  Tab,
  Toolbar,
  Typography
} from '@material-ui/core';

import useFetch from 'use-http-2';
import { useSnackbar } from 'notistack';
import SwipeableViews from 'react-swipeable-views';

import Loading from '../../components/Loading';
import TeamsContext from '../../contexts/Teams';

import useRouteParams from './useRouteParams';
import Pods from './Pods';
import Metrics from './Metrics';

const Header: FunctionComponent = () => {
  const { clusterId, workerName } = useRouteParams();
  return (
    <Toolbar disableGutters variant="dense">
      <Breadcrumbs aria-label="breadcrumb">
        <UILink color="inherit" component={RouterLink} to="../">
          Clusters
        </UILink>
        <UILink color="inherit" component={RouterLink} to="./">
          {clusterId}
        </UILink>
        <Typography color="textPrimary">{workerName}</Typography>
      </Breadcrumbs>
    </Toolbar>
  );
}

const TabView: FunctionComponent<{ data: any }> = ({ data }) => {
  const [index, setIndex] = useState(0);

  const handleChange = useCallback((event: ChangeEvent<{}>, value: number) => {
    setIndex(value);
  }, [setIndex]);
  const handleChangeIndex = useCallback((index: number) => {
    setIndex(index);
  }, [setIndex]);

  return (
    <Paper elevation={2}>
      <Tabs
        value={index}
        variant="fullWidth"
        textColor="primary"
        indicatorColor="primary"
        onChange={handleChange}
      >
        <Tab label="Pods"/>
        <Tab label="Metrics"/>
      </Tabs>
      <SwipeableViews
        index={index}
        onChangeIndex={handleChangeIndex}
      >
        <Hidden implementation="css" xsUp={index !== 0}>
          <Pods data={data}/>
        </Hidden>
        <Hidden implementation="css" xsUp={index !== 1}>
          <Metrics data={data}/>
        </Hidden>
      </SwipeableViews>
    </Paper>
  )
}

const Content: FunctionComponent = () => {
  const { clusterId, workerName } = useRouteParams();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { selectedTeam } = useContext(TeamsContext);
  const { data, error, loading, get } = useFetch(
    `/api/v2/clusters/${clusterId}/teams/${selectedTeam}`,
    undefined,
    [clusterId, selectedTeam]
  );

  const workerData = useMemo(() => {
    if (data === undefined) return data;
    return data.workers[workerName];
  }, [data, workerName]);

  useEffect(() => {
    if (!loading) {
      const timeout = setTimeout(get, 3000)
      return () => { clearTimeout(timeout); }
    }
  }, [loading, get]);

  useEffect(() => {
    if (error) {
      const message = `Failed to fetch status of cluster ${clusterId}`
      const key = enqueueSnackbar(message, {
        variant: 'error',
        persist: true
      });
      return () => {
        if (key != null) {
          closeSnackbar(key);
        }
      }
    }
  }, [error, clusterId, enqueueSnackbar, closeSnackbar]);

  return (
    <>
      <Helmet title={`${workerName} - ${clusterId}`}/>
      <Container maxWidth="lg">
        <Header/>
        { workerData === undefined && <Loading/> }
        { workerData !== undefined && <TabView data={workerData}/> }
      </Container>
    </>
  );

}

const Worker: FunctionComponent = () => {
  const { clusterId, workerName } = useRouteParams();

  return <Content key={`${clusterId}/${workerName}`}/>;
};

export default Worker;
