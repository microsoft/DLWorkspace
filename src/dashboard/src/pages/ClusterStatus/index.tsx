import React, {FC, useEffect, useState} from "react";
import SwipeableViews from 'react-swipeable-views';
import {
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

const ClusterStatus: FC = () => {
  const theme = useTheme();
  const [value, setValue] = React.useState(0);
  const {clusters} = React.useContext(ClusterContext);
  const { selectedTeam } = React.useContext(TeamContext);
  const [selectedValue, setSelectedValue] = useState("");
  const [vcStatus, setVcStatus] = useState([]);
  const [userStatus, setUserStatus] = useState(Array());
  const [nodeStatus, setNodeStatus] = useState([]);
  const[showIframe, setShowIframe] = useState(true);
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
    if (clusters) {
      const params = new URLSearchParams({
        query:`count+(task_gpu_percent{vc_name="${selectedTeam}"}+==+0)+by+(username)`,
      });
      const paramsVc = new URLSearchParams({
        vc:`${selectedTeam}`,
      });
      const filterclusters = convertToArrayByKey(clusters, 'id');
      setSelectedValue(filterclusters[0]);
      if (localStorage.getItem("selectedCluster")) {
        setSelectedValue((String)(localStorage.getItem("selectedCluster")));
      } else {
        if (selectedValue === '') {
          setSelectedValue(filterclusters[0]);
        }
      }
      let fetchs: any = [];
      filterclusters.forEach((cluster) => {
        fetchs.push(fetchVC(cluster));
      })
      Promise.all(fetchs).then((res: any) => {
        //init user status & node status when loading page
        console.log(res)
        let userfetchs: any = [];
        console.log()
        if (localStorage.getItem("selectedCluster") === null)  {
          userfetchs = res[0];
        } else {
          console.log('test')
          userfetchs = res.filter((vc: any) => vc['ClusterName'] === localStorage.getItem('selectedCluster'))[0];
        }
        console.log(userfetchs)
        let fetchUsrs: any = []
        for (let fetchedUser of userfetchs['user_status'] ) {
          let tmpUser: any ={};
          tmpUser['userName'] = fetchedUser['userName'];
          tmpUser['usedGPU'] = (String)(Object.values(fetchedUser['userGPU'])[0]);
          fetchUsrs.push(tmpUser)
        }
        console.log('--->', fetchUsrs)

        let fetchUsrsStatus = [];
        fetchUsrsStatus.push(fetch(userfetchs['idleGPUUrl']+paramsVc));
        fetchUsrsStatus.push(fetch(decodeURIComponent(userfetchs['getIdleGPUPerUserUrl']+params)));
        let prometheusResp: any = [];
        let fetchIdes: any = [];
        Promise.all(fetchUsrsStatus).then((responses: any) => {
          responses.forEach(async (response: any)=>{
            const res = await response.json();
            console.log(res)
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
            let tmpMerged = _.values(mergeTwoObjsByKey(fetchIdes,fetchUsrs,'userName'));
            _.values(tmpMerged).forEach((mu: any)=>{
              if (!mu.hasOwnProperty('usedGPU')) {
                mu['usedGPU'] = "0";
              }
              if (!mu.hasOwnProperty('idleGPU')) {
                mu['idleGPU'] = "0";
              }
              if (!mu.hasOwnProperty('booked')) {
                mu['booked'] = "0";
              }
              if (!mu.hasOwnProperty('idle')) {
                mu['idle'] = "0";
              }
            });
            let finalUserStatus = _.values(mergeTwoObjsByKey(tmpMerged,prometheusResp,'userName'));
            let totalRow: any = {};
            totalRow['userName'] = 'Total';
            totalRow['booked'] = 0;
            totalRow['idle'] = 0;
            totalRow['usedGPU'] = 0;
            totalRow['idleGPU'] = 0;
            for (let us of finalUserStatus) {
              console.log(us);
              totalRow['booked'] += us['booked'];
              totalRow['idle'] += us['idle'];
              totalRow['usedGPU'] += parseInt(us['usedGPU']);
              totalRow['idleGPU'] += parseInt(us['idleGPU']);
            }
            finalUserStatus.push(totalRow);

            setUserStatus(finalUserStatus)

          })
        })

        setIframeUrl(userfetchs['GranaUrl'] );
        console.log(userfetchs['GranaUrl'])
        setNodeStatus(userfetchs['node_status']);
        setIframeUrlForPerVC(userfetchs['GPUStatisticPerVC']);
        console.log(userfetchs['GPUStatisticPerVC'])
        setVcStatus(res);
      })
    }
  }

  useEffect(()=>{
    localStorage.removeItem('selectedCluster')
    let mount = true;
    let timeout: any;
    if (mount) {
      fetchClusterStatus()
      timeout = setTimeout(() => {fetchClusterStatus()},30000)
    }

    return () => {
      mount = false;
      clearTimeout(timeout)
    }
  },[clusters, selectedTeam])
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedValue(event.target.value);
    localStorage.setItem('selectedCluster', event.target.value);
    const filteredVCStatus: any = vcStatus.filter((vc)=>vc['ClusterName'] === event.target.value);
    console.log(vcStatus)
    fetchClusterStatus()
    setNodeStatus(filteredVCStatus[0]['node_status']);
    setIframeUrl((filteredVCStatus[0]['GranaUrl']));
  }
  if (vcStatus){
    return (
      <>
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
            <TeamVCUserStatus userStatus={userStatus} currentCluster={selectedValue} showCurrentUser={showCurrentUser} handleSwitch={handleSwitch}/>
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={2} dir={theme.direction} title={ClusterUsagesTitles[0]}>
            <ClusterUsage showIframe={showIframe} iframeUrl={iframeUrlForPerVC}/>
            <Typography component="h2" variant="h6" style={{ marginLeft:'20px' }}>
              {ClusterUsagesTitles[1]}
            </Typography>
            <ClusterUsage showIframe={showIframe} iframeUrl={iframeUrl}/>
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={3} dir={theme.direction} title={ClusterStatusTitles[value]}>
            <PhysicalClusterNodeStatus nodeStatus={  nodeStatus }/>
          </DLTSTabPanel>
        </SwipeableViews>
      </>
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

