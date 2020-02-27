import React, {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useState
} from 'react';
import {
  useHistory,
  useParams
} from 'react-router-dom';
import {
  Container,
  FormControl,
  InputLabel,
  Paper,
  Tabs,
  Tab,
  Toolbar
} from '@material-ui/core';
import SwipeableViews from 'react-swipeable-views';

import ClustersContext from '../../contexts/Clusters';
import ClusterSelector from '../../components/ClusterSelector';

import Loading from '../../components/Loading';
import ClusterContext from './ClusterContext';
import MyJobs from './MyJobs';
import AllJobs from './AllJobs';

interface RouteParams {
  clusterId: string;
}

const TabView: FunctionComponent = () => {
  const [index, setIndex] = useState(0);
  const onChange = useCallback((event: ChangeEvent<{}>, value: any) => {
    setIndex(value as number);
  }, [setIndex]);
  const onChangeIndex = useCallback((index: number, prevIndex: number) => {
    setIndex(index);
  }, [setIndex]);
  return (
    <>
      <Tabs
        value={index}
        onChange={onChange}
        variant="fullWidth"
        textColor="primary"
        indicatorColor="primary"
      >
        <Tab label="My Jobs"/>
        <Tab label="All Jobs"/>
      </Tabs>
      <SwipeableViews
        index={index}
        onChangeIndex={onChangeIndex}
      >
        {index === 0 ? <MyJobs/> : <div/>}
        {index === 1 ? <AllJobs/> : <div/>}
      </SwipeableViews>
    </>
  );
}

const ClusterJobs: FunctionComponent<{ cluster: any }> = ({ cluster }) => {
  return (
    <ClusterContext.Provider value={{ cluster: cluster }}>
      <Paper elevation={2}>
        {cluster.admin ? <TabView/> : <MyJobs/>}
      </Paper>
    </ClusterContext.Provider>
  );
}

const Jobs: FunctionComponent = () => {
  const { clusters } = useContext(ClustersContext);

  const history = useHistory();
  const { clusterId } = useParams<RouteParams>();

  const cluster = useMemo(() => {
    return clusters.filter(cluster => cluster.id === clusterId)[0]
  }, [clusters, clusterId]);

  const onClusterChange = useCallback((cluster: any) => {
    history.replace(`/jobs-v2/${cluster.id}`)
  }, [history]);

  return (
    <Container fixed maxWidth="xl">
      <Toolbar disableGutters>
        <FormControl fullWidth>
          <InputLabel>Choose Cluster</InputLabel>
          <ClusterSelector defaultId={clusterId} onChange={onClusterChange}/>
        </FormControl>
      </Toolbar>
      {
        cluster !== undefined
          ? <ClusterJobs key={cluster.id} cluster={cluster}/>
          : <Loading/>
      }
    </Container>
  );
};

export default Jobs;
