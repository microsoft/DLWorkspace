import React, {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useState
} from 'react';
import { useParams } from 'react-router';
import { Link as RouterLink } from 'react-router-dom';
import { Helmet } from 'react-helmet';
import SwipeableViews from 'react-swipeable-views';
import {
  Breadcrumbs,
  Container,
  Hidden,
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
import Metrics from './Metrics';

const Header: FunctionComponent = () => {
  const { clusterId } = useParams();
  return (
    <Toolbar disableGutters variant="dense">
      <Breadcrumbs aria-label="breadcrumb">
        <UILink color="inherit" component={RouterLink} to="../">
          Clusters
        </UILink>
        <Typography color="textPrimary">{clusterId}</Typography>
      </Breadcrumbs>
    </Toolbar>
  );
};

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
        <Tab label="Users"/>
        <Tab label="Workers"/>
        <Tab label="Metrics"/>
      </Tabs>
      <SwipeableViews
        index={index}
        onChangeIndex={handleChangeIndex}
      >
        <Hidden implementation="css" xsUp={index !== 0}>
          <Users users={data.users}/>
        </Hidden>
        <Hidden implementation="css" xsUp={index !== 1}>
          <Workers types={data.types} workers={data.workers}/>
        </Hidden>
        <Hidden implementation="css" xsUp={index !== 2}>
          <Metrics/>
        </Hidden>
      </SwipeableViews>
    </Paper>
  )
}

const ClusterContent: FunctionComponent = () => {
  const { clusterId } = useParams();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { selectedTeam } = useContext(TeamsContext);
  const { data, error, loading, get } = useFetch(
    `/api/v2/clusters/${clusterId}/teams/${selectedTeam}`,
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
        { data === undefined && <Loading/> }
        { data !== undefined && <TabView data={data}/> }
      </Container>
    </>
  );
}

const Cluster: FunctionComponent = () => {
  const { clusterId } = useParams();
  return <ClusterContent key={clusterId}/>;
}

export default Cluster;
