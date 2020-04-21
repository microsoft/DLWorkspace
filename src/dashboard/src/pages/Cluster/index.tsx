import React, {
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

import TeamsContext from '../../contexts/Teams';
import Loading from '../../components/Loading';

import Users from './Users';
import Workers from './Workers';
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
  const [query, setQuery] = useState<{ current: string }>();

  const handleChange = useCallback((event: ChangeEvent<{}>, value: number) => {
    setIndex(value);
  }, [setIndex]);
  const handleChangeIndex = useCallback((index: number) => {
    setIndex(index);
  }, [setIndex]);

  const handleSearchPods = useCallback((query: string) => {
    setQuery({ current: query });
  }, [setQuery]);

  useEffect(() => {
    if (query !== undefined) {
      setIndex(2); // Pods
    }
  }, [query]);

  return (
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
        <Tab label="Pods"/>
        <Tab label="Metrics"/>
      </Tabs>
      <SwipeableViews
        index={index}
        onChangeIndex={handleChangeIndex}
      >
        {index === 0 ? <Users data={data} onSearchPods={handleSearchPods}/> : <div/>}
        {index === 1 ? <Workers data={data} onSearchPods={handleSearchPods}/> : <div/>}
        {index === 2 ? <Pods data={data} query={query && query.current}/> : <div/>}
        {index === 3 ? <Metrics data={data}/> : <div/>}
      </SwipeableViews>
    </Paper>
  )
}

const ClusterContent: FunctionComponent = () => {
  const { clusterId } = useParams();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { selectedTeam } = useContext(TeamsContext);

  const { data, error, loading, get } = useFetch(
    `/api/v2/teams/${selectedTeam}/clusters/${clusterId}`,
    undefined,
    [clusterId, selectedTeam]
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
        {data !== undefined ? <TabView data={data}/> : <Loading/>}
      </Container>
    </>
  );
}

const Cluster: FunctionComponent = () => {
  const { clusterId } = useParams();
  return <ClusterContent key={clusterId}/>;
}

export default Cluster;
