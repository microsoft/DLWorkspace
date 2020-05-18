import * as React from 'react';
import {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useState
} from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet';
import SwipeableViews from 'react-swipeable-views';
import {
  Breadcrumbs,
  Container,
  Link as UILink,
  Tabs,
  Tab,
  Toolbar,
  Typography,
  Paper,
} from '@material-ui/core';
import useFetch from 'use-http-2';
import { useSnackbar } from 'notistack';

import TeamContext from '../../contexts/Team';
import Loading from '../../components/Loading';

import { QueryProvider } from './QueryContext';
import Users from './Users';
import Workers from './Workers';
import Storages from './Storages';
import Pods from './Pods';
import Metrics from './Metrics';

const Header: FunctionComponent = () => {
  const { clusterId } = useParams();
  return (
    <Toolbar disableGutters variant="dense">
      <Breadcrumbs aria-label="breadcrumb">
        <UILink color="inherit" component={RouterLink} to="./">
          Clusters
        </UILink>
        <Typography color="textPrimary">{clusterId}</Typography>
      </Breadcrumbs>
    </Toolbar>
  );
};

interface TabViewProps {
  data: any;
}

const TabView: FunctionComponent<TabViewProps> = ({ data }) => {
  const [index, setIndex] = useState(0);

  const handleChange = useCallback((event: ChangeEvent<{}>, value: number) => {
    setIndex(value);
  }, [setIndex]);
  const handleChangeIndex = useCallback((index: number) => {
    setIndex(index);
  }, [setIndex]);

  const handleQueryChanged = useCallback(() => {
    setIndex(3); // Pods
  }, [setIndex]);

  return (
    <QueryProvider onQueryChanged={handleQueryChanged}>
      <Paper elevation={2}>
        <Tabs
          value={index}
          variant="fullWidth"
          textColor="primary"
          indicatorColor="primary"
          onChange={handleChange}
        >
          <Tab label="Users"/>
          <Tab label="Workers"/>
          <Tab label="Storages"/>
          <Tab label="Pods"/>
          <Tab label="Metrics"/>
        </Tabs>
        <SwipeableViews
          index={index}
          onChangeIndex={handleChangeIndex}
        >
          {index === 0 ? <Users data={data}/> : <div/>}
          {index === 1 ? <Workers data={data}/> : <div/>}
          {index === 2 ? <Storages data={data}/> : <div/>}
          {index === 3 ? <Pods data={data}/> : <div/>}
          {index === 4 ? <Metrics data={data}/> : <div/>}
        </SwipeableViews>
      </Paper>
    </QueryProvider>
  )
}

const ClusterContent: FunctionComponent = () => {
  const { clusterId } = useParams();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { currentTeamId } = useContext(TeamContext);

  const { data, error, loading, get } = useFetch(
    `/api/v2/teams/${currentTeamId}/clusters/${clusterId}`,
    undefined,
    [clusterId, currentTeamId]
  );

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
      <Helmet title={clusterId}/>
      <Container maxWidth="lg">
        <Header/>
        {data !== undefined ? <TabView data={data}/> : <Loading>Fetching Cluster Status</Loading>}
      </Container>
    </>
  );
}

const Cluster: FunctionComponent = () => {
  const { clusterId } = useParams();
  return <ClusterContent key={clusterId}/>;
}

export default Cluster;
