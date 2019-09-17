import React, {Fragment, useEffect, useState} from 'react';
import {
  Theme,
  useTheme,
  Box,
  Tab,
  Tabs,
  makeStyles,
  createStyles,
  AppBar,
  Container,
  CircularProgress,
  useMediaQuery, Snackbar, SnackbarContent,
} from '@material-ui/core';
import { useGet } from 'use-http';

import UserContext from '../../../contexts/User';
import Context from './Context';
import Brief from './Brief';
import RunCommand from './RunCommand';
import Log from './Log';
import Monitor from './Monitor';
import Endpoints from './Endpoints';
import { TabPanel } from '../../CommonComponents/TabPanel'
import {a11yProps} from "../../CommonComponents/a11yProps";
import SwipeableViews from "react-swipeable-views";
import theme from "../../../contexts/MonospacedTheme";
import {green} from "@material-ui/core/colors";
interface Props {
  clusterId: string;
  jobId: string;
  job: any;
}

const JobDetails: React.FC<Props> = ({ clusterId, jobId, job }) => {
  const { email } = React.useContext(UserContext);
  const [cluster] = useGet(`/api/clusters/${clusterId}`, { onMount: true });
  const [value, setValue] = React.useState(0);
  const theme = useTheme();
  const[showIframe, setShowIframe] = useState(false);
  const handleChangeTab = (event: React.ChangeEvent<{}>, newValue: number) => {
    setShowIframe(false)
    setTimeout(()=>{
      setShowIframe(true);
    },2000);
    setValue(newValue);
  }
  const handleChangeIndex = (index: number) => {
    setValue(index);
  }
  const isReadOnly = (email !== job['userName']);
  useEffect(()=>{
    let mount = true;
    let timeout: any;
    timeout = setTimeout(()=>{
      setShowIframe(true);
    },2000);
    return () => {
      mount = false;
      clearTimeout(timeout)
    }
  },[])
  const isDesktop = useMediaQuery(theme.breakpoints.up("sm"));
  const [showOpen, setshowOpen] = useState(false)
  const handleWarnClose = () => {
    setshowOpen(false)
  }
  if (isReadOnly) {
    return (
      <Context.Provider value={{ jobId, clusterId, job, cluster }}>
        <Container maxWidth={isDesktop ? 'lg' : 'xs'} >
          <AppBar position="static" color="default">
            <Tabs
              value={value}
              onChange={handleChangeTab}
              indicatorColor="primary"
              textColor="primary"
              variant="fullWidth"
              aria-label="full width tabs example"
            >
              <Tab label="Brief" {...a11yProps(0)} />
              <Tab label=" Job analytics and monitoring" {...a11yProps(2)} />
              <Tab label=" Console Output" {...a11yProps(3)} />
            </Tabs>
          </AppBar>
        </Container>
        <SwipeableViews
          axis={theme.direction === 'rtl' ? 'x-reverse' : 'x'}
          index={value}
          onChangeIndex={handleChangeIndex}
        >
          <TabPanel value={value} index={0} dir={theme.direction}>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Brief/></Container>
          </TabPanel>
          <TabPanel value={value} index={1} dir={theme.direction}>
            { showIframe ? cluster && <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Monitor/></Container> :  <CircularProgress/>}
          </TabPanel>
          <TabPanel value={value} index={2} dir={theme.direction}>
            { job['log'] && <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Log/></Container> }
          </TabPanel>
        </SwipeableViews>

      </Context.Provider>
    );
  } else {
    return (
      <Context.Provider value={{ jobId, clusterId, job, cluster }}>
        <Container maxWidth={isDesktop ? 'lg' : 'xs'} >
          <AppBar position="static" color="default">
            <Tabs
              value={value}
              onChange={handleChangeTab}
              indicatorColor="primary"
              textColor="primary"
              variant="fullWidth"
              aria-label="full width tabs example"
            >
              <Tab label="Brief" {...a11yProps(0)} />
              <Tab label="Mapped Endpoints" {...a11yProps(1)} />
              {/*<Tab label="Run Command" {...a11yProps(2)} />*/}
              <Tab label=" Job analytics and monitoring" {...a11yProps(2)} />
              <Tab label=" Console Output" {...a11yProps(3)} />
            </Tabs>
          </AppBar>
          <SwipeableViews
            axis={theme.direction === 'rtl' ? 'x-reverse' : 'x'}
            index={value}
            onChangeIndex={handleChangeIndex}
          >
            <TabPanel value={value} index={0} dir={theme.direction}>
              <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Brief/></Container>
            </TabPanel>
            <TabPanel value={value} index={1} dir={theme.direction}>
              {(job['jobStatus'] !== 'pausing' && job['jobStatus'] !== 'paused') &&  <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Endpoints setOpen={setshowOpen}/></Container>}
            </TabPanel>
            <TabPanel value={value} index={2} dir={theme.direction}>
              { showIframe ? cluster && <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Monitor/></Container> :  <CircularProgress/>}
            </TabPanel>
            <TabPanel value={value} index={3} dir={theme.direction}>
              { job['log'] && <Box marginTop={2}><Log/></Box> }
            </TabPanel>
          </SwipeableViews>
          <Snackbar
            anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
            open={showOpen}
            autoHideDuration={1000}
            onClose={handleWarnClose}
            ContentProps={{
              'aria-describedby': 'message-id',
            }}
          >
            <SnackbarContent
              style={{backgroundColor:green[400]}}
              aria-describedby="client-snackbar"
              message={<span id="message-id" >{"Copied"}</span>}
            />
          </Snackbar>
        </Container>
      </Context.Provider>
    );
  }
};

export default JobDetails;
