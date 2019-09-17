import React, {FC, Fragment, useEffect, useState} from "react";
import SwipeableViews from 'react-swipeable-views';
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Toolbar,
  Typography,
  Tabs,
  Tab,
  AppBar,
  Box,
  Radio,
  Switch,
  Tooltip,
  Theme,
  useTheme,
  createStyles,
  makeStyles,
  CircularProgress,
  Container,
  useMediaQuery,
  createMuiTheme,
  MuiThemeProvider
} from "@material-ui/core";
import { TabPanel } from '../CommonComponents/TabPanel'
import TeamContext from "../../contexts/Teams";
import ClusterContext from '../../contexts/Clusters';
import {a11yProps} from '../CommonComponents/a11yProps';
import ServicesChips from "./components/ServicesChips";
import useFetch from "use-http/dist";
import Iframe from 'react-iframe'
import MaterialTable, {MTableToolbar} from 'material-table';
import _ from "lodash";
import theme from "../../contexts/MonospacedTheme";
const useStyles = makeStyles((theme: Theme) => {
  return createStyles({
    root: {
      backgroundColor: theme.palette.background.paper,
      width: 500,
    },
    paperMargin: {
      marginTop: '10px',
    },
  });
});
const tableTheme = createMuiTheme({
  overrides: {
    MuiTableCell: {
      root: {
        paddingTop: 4,
        paddingBottom: 4,
        paddingLeft:2,
        paddingRight:4,
      }
    }
  }
});


const ClusterStatus: FC = () => {
  const styles = useStyles();
  const theme = useTheme();
  const [value, setValue] = React.useState(0);
  const {clusters} = React.useContext(ClusterContext);
  const { selectedTeam,teams } = React.useContext(TeamContext);
  const [selectedValue, setSelectedValue] = useState("");
  const [vcStatus, setVcStatus] = useState([]);
  const [userStatus, setUserStatus] = useState([]);
  const [nodeStatus, setNodeStatus] = useState([]);
  const[showIframe, setShowIframe] = useState(false);
  const[iframeUrl,setIframeUrl] = React.useState('');
  const[iframeUrlForPerVC, setIframeUrlForPerVC] = React.useState('');
  const [showCurrentUser, setShowCurrentUser] = useState(true);
  const handleSwitch = () => {
    setShowCurrentUser(!showCurrentUser);
  }
  const options = {
    onMount: true
  }
  const fetchVcStatusUrl = `/api`;
  const fetchiGrafanaUrl = `/api/clusters`;

  const request = useFetch(fetchVcStatusUrl,options);
  const requestGrafana = useFetch(fetchiGrafanaUrl, options);
  const fetchVC = async (cluster: string) => {
    const response = await request.get(`/teams/${selectedTeam}/clusters/${cluster}`);
    const {grafana, prometheus} = await requestGrafana.get(`/${cluster}`);
    const idleGPUUrl = prometheus.replace("9091","9092");
    const getIdleGPUPerUser = `${prometheus}/prometheus/api/v1/query?`;

    response['getIdleGPUPerUserUrl'] = getIdleGPUPerUser;
    response['idleGPUUrl'] = `${idleGPUUrl}/gpu_idle?`;
    response['ClusterName'] = cluster;
    response['GranaUrl'] = `${grafana}/dashboard/db/gpu-usage?refresh=30s&orgId=1&_=${Date.now()}`;
    response['GPUStatisticPerVC'] = `${grafana}/dashboard/db/per-vc-gpu-statistic?var-vc_name=${selectedTeam}&_=${Date.now()}`;
    response['prometheus'] = prometheus;
    return response;
  }
  const fetchClusterStatus = () => {
    setVcStatus([]);
    if (clusters) {
      const params = new URLSearchParams({
        query:`count+(task_gpu_percent{vc_name="${selectedTeam}"}+==+0)+by+(username)`,
      });
      const paramsVc = new URLSearchParams({
        vc:`${selectedTeam}`,
      });
      const filterclusters = _.map(clusters,'id');
      setSelectedValue(filterclusters[0]);
      let fetchs: any = [];
      filterclusters.forEach((cluster) => {
        fetchs.push(fetchVC(cluster));
      })
      Promise.all(fetchs).then((res: any) => {
        //init user status & node status when loading page
        let fetchUsrs: any = []
        for (let fetchedUser of res[0]['user_status']) {
          let tmpUser: any ={};
          tmpUser['userName'] = fetchedUser['userName'];
          tmpUser['usedGPU'] = (String)(Object.values(fetchedUser['userGPU'])[0]);
          fetchUsrs.push(tmpUser)
        }

        let fetchUsrsStatus = [];
        fetchUsrsStatus.push(fetch(res[0]['idleGPUUrl']+paramsVc));
        fetchUsrsStatus.push(fetch(decodeURIComponent(res[0]['getIdleGPUPerUserUrl']+params)));
        Promise.all(fetchUsrsStatus).then((responses: any) => {
          responses.forEach(async (response: any)=>{
            const res = await response.json();
            let prometheusResp: any = [];
            let fetchIdes: any = [];
            if (res['data']) {
              for (let item of res['data']["result"]) {
                let idleUser: any = {};
                idleUser['userName'] = item['metric']['username'];
                idleUser['idleGPU'] = item['value'][1];
                prometheusResp.push(idleUser)
              }
            } else {
              for (let [key, value]  of Object.entries(res)) {
                let idleTmp: any = {}
                idleTmp['userName'] = key;
                let arr: any = value;
                idleTmp['booked'] = Math.floor(arr['booked'] / 3600);
                idleTmp['idle'] = Math.floor(arr['idle'] / 3600);
                fetchIdes.push(idleTmp);
              }
            }
            const merged = _.merge(_.keyBy(fetchUsrs, 'userName'), _.keyBy(prometheusResp, 'userName'));
            let mergedUsers: any = _.values(merged);
            mergedUsers.forEach((us: any)=>{
              if (!us.hasOwnProperty('usedGPU')) {
                us['usedGPU'] = "0";
              }
            })
            const mergedTmp = _.merge(_.keyBy(mergedUsers, 'userName'), _.keyBy(fetchIdes, 'userName'));
            let mergedTmpUpdate: any = _.values(mergedTmp);
            mergedTmpUpdate.forEach((mu: any)=>{
              if (!mu.hasOwnProperty('usedGPU')) {
                mu['usedGPU'] = "0";
              }
              if (!mu.hasOwnProperty('idleGPU')) {
                mu['idleGPU'] = "0";
              }
            })
            if (mergedTmpUpdate.length > 0 && fetchIdes.length === mergedTmpUpdate.length) {
              setUserStatus(mergedTmpUpdate)
            }
          })
        })

        setIframeUrl(res[0]['GranaUrl'] );
        setNodeStatus(res[0]['node_status']);
        setIframeUrlForPerVC(res[0]['GPUStatisticPerVC']);
        setVcStatus(res);
      })
    }
  }

  useEffect(()=>{
    let mount = true;
    let timeout: any;
    let timeout1: any;
    if (mount) {
      fetchClusterStatus()
      timeout = setTimeout(() => {fetchClusterStatus()},30000)
    }
    timeout1 = setTimeout(()=>{
      setShowIframe(true);
    },2000);
    return () => {
      mount = false;
      clearTimeout(timeout)
      clearTimeout(timeout1)
    }
  },[clusters, selectedTeam])
  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    setSelectedValue(event.target.value);
    const filteredVCStatus: any = vcStatus.filter((vc)=>vc['ClusterName'] === event.target.value);
    setUserStatus((filteredVCStatus['user_status']));
    setNodeStatus((filteredVCStatus['node_status']));
    setIframeUrl((filteredVCStatus['GranaUrl']));

  }
  const isEmpty = (obj: object) => {
    for(let key in obj) {
      if(obj.hasOwnProperty(key))
        return false;
    }
    return true;
  }
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
  const isDesktop = useMediaQuery(theme.breakpoints.up("sm"));
  if (vcStatus){
    return (
      <Fragment>
        <Container maxWidth={isDesktop ? 'lg' : 'xs'}  >
          <AppBar position="static" color="default">
            <Tabs
              value={value}
              onChange={handleChangeTab}
              indicatorColor="primary"
              textColor="primary"
              variant="fullWidth"
              aria-label="full width tabs example"
            >
              <Tab label="Team Virtual Cluster Status" {...a11yProps(0)} />
              <Tab label="Team VC User Status" {...a11yProps(1)} />
              <Tab label="Cluster Usage" {...a11yProps(2)} />
              <Tab label=" Physical Cluster Node Status" {...a11yProps(3)} />
            </Tabs>
          </AppBar>
        </Container>
        <SwipeableViews
          axis={theme.direction === 'rtl' ? 'x-reverse' : 'x'}
          index={value}
          onChangeIndex={handleChangeIndex}
        >
          <TabPanel value={value} index={0} dir={theme.direction}>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'}>
              <Paper className={styles.paperMargin} style={{ display: isDesktop ? 'block' : 'inline-block' }}>
                <Toolbar>
                  <Typography component="h2" variant="h6">
                    Team Virtual Cluster Status:
                  </Typography>
                </Toolbar>
                <Table size={"small"}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Total GPU</TableCell>
                      <TableCell>Reserved GPU</TableCell>
                      <TableCell>Used GPU</TableCell>
                      <TableCell>Available GPU</TableCell>
                      <TableCell>Active Jobs</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {
                      vcStatus ? vcStatus.map(( vcs, idx) => {
                        const gpuCapacity =  isEmpty(Object.values(vcs['gpu_capacity'])) ? 0 : (String)(Object.values(vcs['gpu_capacity'])[0]);
                        const gpuAvailable = isEmpty (Object.values(vcs['gpu_avaliable'])) ? 0 : (String)(Object.values(vcs['gpu_avaliable'])[0]);
                        const gpuUnschedulable = isEmpty(Object.values(vcs['gpu_unschedulable'])) ? 0 : (String)(Object.values(vcs['gpu_unschedulable'])[0]);
                        const gpuUsed =  isEmpty(Object.values(vcs['gpu_used'])) ? 0 : (String)(Object.values(vcs['gpu_used'])[0]);
                        return (
                          <>
                            <TableRow key="idx">
                              <TableCell key={vcs['ClusterName']}>
                                <Radio
                                  checked={selectedValue === vcs['ClusterName']}
                                  onChange={handleChange}
                                  value={vcs['ClusterName']}
                                  name={vcs['ClusterName']}
                                  inputProps={{'aria-label': vcs['ClusterName']}} />
                                {vcs['ClusterName']}
                              </TableCell>
                              <TableCell key="gpuCapacity">
                                {gpuCapacity}
                              </TableCell>
                              <TableCell key="gpuUnschedulable">
                                {gpuUnschedulable}
                              </TableCell>
                              <TableCell key="gpuUsed">
                                {gpuUsed}
                              </TableCell>
                              <TableCell key="gpuAvailable">
                                {gpuAvailable}
                              </TableCell>
                              <TableCell key="vcs['AvaliableJobNum']">
                                {vcs['AvaliableJobNum']}
                              </TableCell>
                            </TableRow>
                          </>
                        )
                      }) : null
                    }

                  </TableBody>
                </Table>
              </Paper>
            </Container>
          </TabPanel>
          <TabPanel value={value} index={1} dir={theme.direction}>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'}>
              {
                userStatus ?  <MaterialTable
                  title="Team VC User Status"
                  columns={[{title: 'Username', field: 'userName'},
                    {title: 'Currently Allocated GPU', field: 'usedGPU',type:'numeric'},
                    {title: 'Currently Idle GPU', field: 'idleGPU',type:'numeric'},
                    {title: 'Past Month Booked GPU Hour', field: 'booked',type:'numeric'},
                    {title: 'Past Month Idle GPU Hour', field: 'idle',type:'numeric'},
                    {title: 'Past Month Idle GPU Hour %', field: 'idle',type:'numeric', render: (rowData: any) => <span style={{ color: Math.floor((rowData['idle'] / rowData['booked']) * 100) > 50 ? "red" : "black" }}>{Math.floor((rowData['idle'] / rowData['booked']) * 100)}</span>, customSort: (a: any, b: any) => {return Math.floor((a['idle'] / a['booked']) * 100) - Math.floor((b['idle'] / b['booked']) * 100)}},]} data={showCurrentUser ? userStatus.filter((uc: any)=>uc['usedGPU'] > 0) : userStatus}
                  options={{filtering: true, sorting: true, exportButton: true,exportFileName: 'Team_VC_User_Report'}}
                  components={{
                    Toolbar: props => (
                      <div>
                        <MTableToolbar {...props} />
                        <Tooltip title="Show Current User" aria-label="add">
                          <Switch
                            checked={showCurrentUser}
                            onChange={handleSwitch}
                            inputProps={{ 'aria-label': 'secondary checkbox' }}
                          />
                        </Tooltip>
                      </div>
                    )
                  }}
                /> :
                  <CircularProgress/>
              }
            </Container>
          </TabPanel>
          <TabPanel value={value} index={2} dir={theme.direction}>
            <Container maxWidth="lg" >
              <Paper className={styles.paperMargin}>
                <Toolbar>
                  <Typography component="h2" variant="h6">
                    VC GPU Usage
                  </Typography>
                </Toolbar>
                {
                  showIframe ?
                    <Iframe url={iframeUrlForPerVC} width="100%" height="400"/> :
                    <CircularProgress/>
                }

              </Paper>
            </Container>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'} >
              <Paper className={styles.paperMargin}>
                <Toolbar>
                  <Typography component="h2" variant="h6">
                    Cluster Usage
                  </Typography>
                </Toolbar>
                {
                  showIframe ?
                    <Iframe url={iframeUrl} width="100%" height="400"/> : <CircularProgress/>
                }
              </Paper>
            </Container>
          </TabPanel>
          <TabPanel value={value} index={3} dir={theme.direction}>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'}>
              <Paper className={styles.paperMargin} style={{ display: isDesktop ? 'block' : 'inline-block' }}>
                <Toolbar>
                  <Typography component="h2" variant="h6">
                    Physical Cluster Node Status:
                  </Typography>
                </Toolbar>
                <MuiThemeProvider theme={isDesktop ? theme : tableTheme}>
                  <Table size={ 'small'} >
                    <TableHead>
                      <TableRow>
                        <TableCell>Node Name</TableCell>
                        <TableCell>Node IP</TableCell>
                        <TableCell>GPU Capacity</TableCell>
                        <TableCell>Used GPU</TableCell>
                        <TableCell>Available GPU</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Services</TableCell>
                        <TableCell>Pods</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {
                        nodeStatus.map((ns,idx) => {
                          const gpuCap = isEmpty(ns['gpu_capacity']) ? 0 :  (Number)(Object.values(ns['gpu_capacity'])[0]);
                          const gpuUsed = isEmpty(ns['gpu_used']) ? 0 : (Number)(Object.values(ns['gpu_used'])[0]);
                          const availableGPU = gpuCap - gpuUsed;
                          const status = ns['unschedulable'] ? "unschedulable" : "ok";
                          let services: string[] = [];
                          for (let service of ns['scheduled_service']) {
                            services.push(`${service}`);
                          }
                          let podStr = '';
                          for (let pod of ns['pods']) {
                            if (!pod.includes("!!!!!!")) {
                              podStr += `<b>[${pod}]</b>`;
                            } else {
                              pod = pod.replace("!!!!!!","");
                              podStr += `<b  variant='h6' style="color:red">[${pod}]</b>`;
                            }
                            podStr += "<br/>";
                          }
                          return  (
                            <TableRow key={idx}>
                              <TableCell key="ns['name']">{ns['name']}</TableCell>
                              <TableCell key="ns['InternalIP']">{ns['InternalIP']}</TableCell>
                              <TableCell key="gpuCap">{gpuCap}</TableCell>
                              <TableCell key="gpuUsed">{gpuUsed}</TableCell>
                              <TableCell key="availableGPU">{availableGPU}</TableCell>
                              <TableCell key="status">{status}</TableCell>
                              <TableCell key="services">
                                {
                                  <ServicesChips services={services}/>
                                }
                              </TableCell>
                              <TableCell key="podStr" dangerouslySetInnerHTML={{ __html: podStr }}></TableCell>
                            </TableRow>
                          )
                        })
                      }
                    </TableBody>
                  </Table>
                </MuiThemeProvider>
              </Paper>
            </Container>
          </TabPanel>
        </SwipeableViews>
      </Fragment>
    )
  } else {
    return (
      <Box display="flex" justifyContent="center">
        <CircularProgress/>
      </Box>
    )
  }

}

export default ClusterStatus;

