import React, {FC, Fragment, useEffect, useState} from "react";
import SwipeableViews from 'react-swipeable-views';
import {
  Paper,
  Toolbar,
  Typography,
  Box,
  Theme,
  useTheme,
  createStyles,
  makeStyles,
  CircularProgress,
} from "@material-ui/core";
import { DLTSTabPanel } from '../CommonComponents/DLTSTabPanel'
import TeamContext from "../../contexts/Teams";
import ClusterContext from '../../contexts/Clusters';
import useFetch from "use-http/dist";

import _ from "lodash";
import { mergeTwoObjsByKey, convertToArrayByKey } from '../../utlities/ObjUtlities';
import {handleChangeIndex} from "../../utlities/interactionUtlties";
import {DLTSTabs} from "../CommonComponents/DLTSTabs";
import {
  ClusterStatusTitles,
  ClusterUsagesTitles
} from "../../Constants/TabsContants";
import {TeamVirtualClusterStatus} from "./components/TeamVirtualClusterStatus";
import {TeamVCUserStatus} from "./components/TeamVCUserStatus";
import {ClusterUsage} from "./components/ClusterUsage";
import {PhysicalClusterNodeStatus} from "./components/PhysicalClusterNodeStatus";

const useStyles = makeStyles((theme: Theme) => {
  return createStyles({
    root: {
      backgroundColor: theme.palette.background.paper,
      width: 500,
    },
    paperMargin: {
      marginTop:'10px',
    }

  });
});

const ClusterStatus: FC = () => {
  const styles = useStyles();
  const theme = useTheme();
  const [value, setValue] = React.useState(0);
  const {clusters} = React.useContext(ClusterContext);
  const { selectedTeam } = React.useContext(TeamContext);
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
      const filterclusters = convertToArrayByKey(clusters, 'id');
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
            const merged = mergeTwoObjsByKey(fetchUsrs, prometheusResp,'userName');
            let mergedUsers: any = _.values(merged);
            mergedUsers.forEach((us: any)=>{
              if (!us.hasOwnProperty('usedGPU')) {
                us['usedGPU'] = "0";
              }
            })
            const mergedTmp = mergeTwoObjsByKey(mergedUsers, fetchIdes, 'userName');
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
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedValue(event.target.value);
    const filteredVCStatus: any = vcStatus.filter((vc)=>vc['ClusterName'] === event.target.value);
    setUserStatus((filteredVCStatus['user_status']));
    setNodeStatus((filteredVCStatus['node_status']));
    setIframeUrl((filteredVCStatus['GranaUrl']));
  }
  if (vcStatus){
    return (
      <Fragment>
        <DLTSTabs value={value} setShowIframe={setShowIframe} setValue={setValue} titles={ClusterStatusTitles} />
        <SwipeableViews
          axis={theme.direction === 'rtl' ? 'x-reverse' : 'x'}
          index={value}
          onChangeIndex={(value) => handleChangeIndex(value, setValue)}
        >
          <DLTSTabPanel value={value} index={0} dir={theme.direction} title={ClusterStatusTitles[value]}>
            <TeamVirtualClusterStatus vcStatus={vcStatus} selectedValue={selectedValue} handleChange={handleChange}/>
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={1} dir={theme.direction} title={ClusterStatusTitles[value]}>
            <TeamVCUserStatus userStatus={userStatus} showCurrentUser={showCurrentUser} handleSwitch={handleSwitch}/>
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={2} dir={theme.direction} title={ClusterUsagesTitles[0]}>
            <ClusterUsage showIframe={showIframe} iframeUrl={iframeUrlForPerVC}/>
            <Paper className={styles.paperMargin}>
              <Toolbar>
                <Typography component="h2" variant="h6">
                  {ClusterUsagesTitles[1]}
                </Typography>
              </Toolbar>
              <ClusterUsage showIframe={showIframe} iframeUrl={iframeUrl}/>
            </Paper>
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={3} dir={theme.direction} title={ClusterStatusTitles[value]}>
            <PhysicalClusterNodeStatus nodeStatus={nodeStatus}/>*
          </DLTSTabPanel>
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

