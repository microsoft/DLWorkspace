import React, {Fragment, useEffect, useRef, useState} from "react";
import {
  Box,
  CircularProgress,
  TextField,
  SvgIcon,
  Tooltip,
  MenuItem,
  Container
} from "@material-ui/core";
import CheckCircleIcon from '@material-ui/icons/CheckCircle';
import { makeStyles, Theme, createStyles } from "@material-ui/core/styles";
import {red, grey, green, blue} from "@material-ui/core/colors";
import { DLTSTabPanel } from '../CommonComponents/DLTSTabPanel'
import {Link} from "react-router-dom";
import useFetch,{usePut} from "use-http/dist";
import MaterialTable from 'material-table';
import useJobs from './useJobs';
import _ from 'lodash';
import ClusterContext from "../../contexts/Clusters";
import useJobsAll from "./useJobsAll";
import IconButton from "@material-ui/core/IconButton";
import DeleteIcon from '@material-ui/icons/Delete';
import CheckIcon from '@material-ui/icons/CheckSharp';
import useCheckIsDesktop from "../../utlities/layoutUtlities";
import {DLTSTabs} from "../CommonComponents/DLTSTabs";
import {JobsTitles} from "../../Constants/TabsContants";
import {JobsOperationDialog} from "./components/JobsOperationDialog";
import {DLTSSnackbar} from "../CommonComponents/DLTSSnackbar";
import {
  SUCCESSFULLYAPPROVED,
  SUCCESSFULLYPAUSED,
  SUCCESSFULLYRESUMED,
  SUCCESSFULLYUPDATEDPRIORITY,
  SUCESSFULKILLED
} from "../../Constants/WarnConstants";
import {convertToArrayByKey} from "../../utlities/ObjUtlities";
import {JobsSelectByCluster} from "./components/JobsSelectByCluster";

const variantIcon = {
  success: CheckCircleIcon,
};
interface Props {
  className?: string;
  message?: string;
  onClose?: () => void;
  variant: keyof typeof variantIcon;
}

const { DateTime } = require('luxon');
const useStyles = makeStyles((theme: Theme) =>
  createStyles({
    root: {
      flexGrow: 1,
      backgroundColor: theme.palette.background.paper
    },
    searchContainer: {
      display: "flex",
      alignItems: "center",
      marginLeft:20,
      marginTop:40
    },
    input: {
      marginLeft: 20,
      flex: 1
    },
    iconButton: {
      padding: 10
    },
    formControl: {
      margin: theme.spacing(1),
      minWidth: 160,

    },
    selectContainer: {
      backgroundColor: theme.palette.background.paper,
      minWidth: 160,
    },
    allow: {
      color: green[500]
    },
    notAllowed:{
      color: red[500]
    },
    linkStyle:{
      textDecoration: 'none',
      color: blue[500],
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
      display: 'inline-block',
      width: '100px',
      overflow: 'hidden',
      '&:hover': {
        height: 'auto',
        wordBbreak:'break-all',
        whiteSpace: 'pre-wrap',
        textDecoration: 'none'
      }
    },
    inputField: {
      fontSize:'12px'
    }
  })
);
const Jobs: React.FC = (props: any) => {
  const classes = useStyles();
  const [value, setValue] = React.useState(0);
  const [refresh, setRefresh] = React.useState(false);
  const handleChange = (event: React.ChangeEvent<{}>, newValue: number) => {
    setRefresh(false);
    setTimeout(()=>{
      setRefresh(true);
    },1000);
    setValue(newValue);
  }
  useEffect(()=>{
    let mount = true;
    let timeout: any;
    timeout = setTimeout(()=>{
      setRefresh(true);
    },1000);
    return () => {
      mount = false;
      clearTimeout(timeout)
    }
  },[])
  const[open, setOpen] = React.useState(false);
  const[openApprove, setOpenApprove] = React.useState(false);
  const[openPause, setOpenPause] = React.useState(false);
  const[openResume, setOpenResume] = React.useState(false);
  const[openKillWarn, setOpenKillWarn] = React.useState(false);
  const[openApproveWarn, setOpenApproveWarn] = React.useState(false);
  const[openPauseWarn, setOpenPauseWarn] = React.useState(false);
  const[openResumeWarn, setOpenResumeWarn] = React.useState(false);
  const[openUpdatePriority,setOpenUpdatePriority] = React.useState(false);
  const [openUpatePriorityWarn, setUpdatePriorityWarn] = React.useState(false);
  const { clusters } = React.useContext(ClusterContext);
  const [currentJob, setCurrentJob] = React.useState({jobId:'',cluster:'',priority: 100});
  const deleteUrl = `/api/clusters/`;
  const requestDelete =  useFetch(deleteUrl);
  const killJob = async () => {
    const body = {"status":"killing"};
    const data = await requestDelete.put(`${currentJob.cluster}/jobs/${currentJob.jobId}/status/`,body);
    return data;
  }
  const approveJob = async () => {
    const body = {"status":"approved"};
    const data = await requestDelete.put(`${currentJob.cluster}/jobs/${currentJob.jobId}/status/`,body);
    return data;
  }
  const pauseJob = async () => {
    const body = {"status":"pausing"};
    const data = await requestDelete.put(`${currentJob.cluster}/jobs/${currentJob.jobId}/status/`,body);
    return data;
  }
  const resumeJob = async () => {
    const body = {"status":"queued"};
    const data = await requestDelete.put(`${currentJob.cluster}/jobs/${currentJob.jobId}/status/`,body);
    return data;
  }
  const { put: setPriority } = usePut('/api');
  const [currentCluster, setCurrentCluster] = useState(props.match.params.cluster ? props.match.params.cluster : Array.isArray(_.map(clusters,'id') )?_.map(clusters,'id')[0] : '');
  const [jobs, error] = useJobs();
  const [allJobs, err] = useJobsAll();

  const filterJobsByCluster = (jobs: any, clusterName: string) => {
    if (clusterName === 'None' || clusterName === '') {
      return jobs;
    } else {
      return jobs.filter((job: any)=>job['cluster'] === clusterName)
    }
  }
  const filterFinishedJobs = (jobs: any) => {
    const filteredJobs = filterJobsByCluster(jobs, currentCluster);
    return filteredJobs.filter((job: any) => job['jobStatus'] !== 'running' &&
                                     job['jobStatus'] !== 'queued' && job['jobStatus'] !== 'unapproved' && job['jobStatus'] !== 'scheduling' &&job['jobStatus'] !== 'pausing' && job['jobStatus'] !== 'paused'  )
  }
  const filterRunningJobs = (jobs: any) => {
    const filteredJobs = filterJobsByCluster(jobs, currentCluster);
    return filteredJobs.filter((job: any) => job['jobStatus'] === 'running')
  }
  const filterQueuedJobs = (jobs: any) => {
    const filteredJobs = filterJobsByCluster(jobs, currentCluster);
    return filteredJobs.filter((job: any) => job['jobStatus'] === 'queued' || job['jobStatus'] === 'scheduling' )
  }
  const filterPauseJobs = (jobs: any) => {
    const filteredJobs = filterJobsByCluster(jobs, currentCluster);
    return filteredJobs.filter((job: any) => job['jobStatus'] === 'paused' || job['jobStatus'] === 'pausing' )
  }
  const filterUnApprovedJobs = (jobs: any) => {
    const filteredJobs = filterJobsByCluster(jobs, currentCluster);
    console.log(filteredJobs.filter((job: any)=>job['jobStatus'] === 'unapproved'))
    return filteredJobs.filter((job: any)=>job['jobStatus'] === 'unapproved');
  }

  const handleClose = () => {
    setOpen(false);
    setOpenApprove(false);
    setOpenPause(false);
    setOpenResume(false);
    setOpenUpdatePriority(false);
  }
  const handleWarnClose = () => {
    setOpenKillWarn(false);
    setOpenApproveWarn(false);
    setOpenPauseWarn(false)
    setOpenResumeWarn(false)
    setUpdatePriorityWarn(false)
  }

  const [message,setMessage] = useState('');


  const handlePriorityKeyPress = (rowData: any,event: React.KeyboardEvent) => {
    //return async () => {
    if (event.key === 'Enter') {
      setCurrentJob({
        jobId: rowData['jobId'],
        cluster:rowData['cluster'],
        priority:(event.target as HTMLInputElement).valueAsNumber
      });
      setOpenUpdatePriority(true);
    }
    //};
  };

  const handleConfirm = () => {
    if (openApprove) {
      approveJob().then((res)=>{
        if (res) {
          setOpenApproveWarn(true);
          setOpenApprove(false);
          setMessage(SUCCESSFULLYAPPROVED);
        } else {
          alert("approve fail")
        }
      })
    } else if (openPause) {
      pauseJob().then((res)=>{
        if (res) {
          setOpenPauseWarn(true);
          setOpenPause(false);
          setMessage(SUCCESSFULLYPAUSED)
        } else {
          alert("pause fail")
        }
      })
    } else if (openResume) {
      resumeJob().then((res)=>{
        if (res) {
          setOpenResumeWarn(true)
          setOpenResume(false);
          setMessage(SUCCESSFULLYRESUMED)
        } else {
          alert("resume fail")
        }
      })
    } else if (openUpdatePriority) {
      setOpenUpdatePriority(false)
      const body = { "priority": currentJob.priority};
      const response = setPriority(`/clusters/${currentJob.cluster}/jobs/${currentJob.jobId}/priority`, body);
      if (response) {
        setUpdatePriorityWarn(true);
        setMessage(SUCCESSFULLYUPDATEDPRIORITY)
      } else {
        alert('Priority set failed');
      }
    } else {
      killJob().then((res)=> {
        if (res) {
          setOpenKillWarn(true);
          setOpen(false)
          setMessage(SUCESSFULKILLED)
        } else {
          alert('kill fail')
        }
      })
    }
  }
  const handlePause = (data: any) => {
    setCurrentJob({
      cluster:data['cluster'],
      jobId: data['jobId'],
      priority:currentJob.priority
    })
    setOpenPause(true);
  }
  const handleResume = (data: any) => {
    setCurrentJob({
      cluster:data['cluster'],
      jobId: data['jobId'],
      priority:currentJob.priority
    })
    setOpenResume(true);
  }
  const renderUserName = (rowData: any)=><span>{rowData['userName'].split("@").shift()}</span>
  const renderPrioritySet = (rowData: any) => <TextField
    key={rowData.jobId}
    type="number"
    label="Priority"
    variant="filled"
    defaultValue={rowData.priority}
    onKeyPress={(event) => handlePriorityKeyPress(rowData, event)}
    fullWidth={true}
    InputProps={{
      classes: {
        input: classes.inputField,
      },
    }}
  />
  const renderDateTime = (rowData: any,time?: string)=> {
    if (time === 'jobTime') {
      return (<span>{ DateTime.fromJSDate(new Date(Date.parse(rowData['jobTime']))).toFormat("yyyy/LL/dd HH:mm:ss")}</span>)
    } else if (time === 'startedAt') {
      return (<span>{ DateTime.fromJSDate(new Date(Date.parse(rowData['jobStatusDetail'][0]['startedAt']))).toFormat("yyyy/LL/dd HH:mm:ss")}</span>)
    } else if (time === 'finishedAt') {
      return (<span>{ DateTime.fromJSDate(new Date(Date.parse(rowData['jobStatusDetail'][0]['finishedAt']))).toFormat("yyyy/LL/dd HH:mm:ss")}</span>)
    }
  }
  const renderActions = (props: any) => {
    if (props.action.icon === 'Pause' && (props.data.jobStatus === 'paused'||props.data.jobStatus === 'pausing')) {
      return (
        <Tooltip title="Resume Job">
          <IconButton style={{ color:green[400] }} size="small" onClick={(event)=>handleResume(props.data)} aria-label="delete">
            <SvgIcon>
              <path d="M8 5v14l11-7z"/><path d="M0 0h24v24H0z" fill="none"/>
            </SvgIcon>
          </IconButton>
        </Tooltip>
      )
    }
    if (props.action.icon === 'Pause') {
      return (
        <Tooltip title="Pause Job">
          <IconButton color="secondary" size="small" onClick={(event)=>handlePause(props.data)} aria-label="delete">
            <SvgIcon>
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/><path d="M0 0h24v24H0z" fill="none"/>
            </SvgIcon>
          </IconButton>
        </Tooltip>
      )
    }
    if (props.action.icon === 'Approve' && props.data.jobStatus === 'unapproved') {
      return(
        <Tooltip title="Approve Job">
          <IconButton color="primary"  size={"small"} aria-label="delete" onClick={(event) => props.action.onClick(event, props.data)}>
            <CheckIcon />
          </IconButton>
        </Tooltip>
      )
    } else if (props.action.icon === 'kill') {
      return(
        <Tooltip title="Kill Job">
          <IconButton color="secondary"  size={"small"} aria-label="delete" onClick={(event) => props.action.onClick(event, props.data)}>
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      )
    } else {
      return null;
    }
  }



  const onClusterChange = (event: React.ChangeEvent<{ value: unknown }>) => {
    setCurrentCluster(event.target.value as string)
  }
  if (jobs && allJobs) {
    console.log(allJobs)
    return (
      <Fragment>
        <JobsOperationDialog handleClose={handleClose}
          titleStyle={{color:red[200]}}
          title={"Info"}
          handleConfirm={handleConfirm}
          job={currentJob}
          openApprove={openApprove}
          openPause={openPause} openResume={openResume} openUpdatePriority={openUpdatePriority} open={open}
        />
        <DLTSTabs value={value} setValue={setValue} titles={JobsTitles}/>
        <DLTSTabPanel value={value} index={0}>
          <Container maxWidth={useCheckIsDesktop ? 'lg' : 'xs'} >
            <JobsSelectByCluster currentCluster={currentCluster} onClusterChange={onClusterChange} clusters={clusters}/>
            <MaterialTable
              title="Running Jobs"
              columns={[
                {title: 'JobId', field: 'jobId', render: rowData =>  <Link className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link>  },
                {title: 'Job Name', field: 'jobName'},
                {title: 'Status', field: 'jobStatus'},
                {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric', customSort: (a: any, b: any) => {
                  return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                } },
                {title: 'Priority', field: 'priority'},
                {title: 'Submitted Time', field: 'jobTime', type: 'date',render:(rowData: any)=>renderDateTime(rowData,"jobTime")},
                {
                  title: 'Preemptible',
                  field: 'jobParams.preemptionAllowed',
                  type: 'boolean'
                },
                {
                  title: 'Started Time',
                  field: 'jobStatusDetail[0].startedAt',
                  type: 'date',
                  emptyValue: 'unknown',
                  render: (rowData: any)=>renderDateTime(rowData, 'startedAt')
                }
              ]}
              data={filterRunningJobs(jobs)}
              options={{
                filtering: false,
                paging: false,
                actionsColumnIndex: -1,
                headerStyle: {
                  backgroundColor: '#7583d1',
                  color: '#fff',
                  whiteSpace: 'nowrap'
                },

              }}
              actions={[
                {
                  icon: 'kill',
                  onClick: (event, rowData: any) => {
                    setOpen(true);
                    setCurrentJob({
                      cluster:rowData['cluster'],
                      jobId: rowData['jobId'],
                      priority:currentJob.priority
                    })
                  }
                },
                {
                  icon: 'Pause',
                  onClick: (event, rowData: any)  => {
                    console.log(rowData);
                  }
                }
              ]}
              components={{
                Action: (props: any) =>
                  renderActions(props)
                ,
              }}
            />
            <MaterialTable
              title="Queued  Jobs"
              columns={[
                {title: 'JobId', field: 'jobId', render: rowData =>  <Link className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link>},
                {title: 'Job Name', field: 'jobName'},
                {title: 'Status', field: 'jobStatus'},
                {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric', customSort: (a: any, b: any) => {
                  return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                } },
                {title: 'Priority', field: 'priority'},
                {title: 'Submitted Time', field: 'jobTime', type: 'date', render: (rowData: any)=>renderDateTime(rowData,'jobTime')},
                {
                  title: 'Preemptible',
                  field: 'jobParams.preemptionAllowed',
                  type: 'boolean'
                }
              ]}
              data={filterQueuedJobs(jobs)}
              options={{
                filtering: false,
                paging: false,
                actionsColumnIndex: -1,
                headerStyle: {
                  backgroundColor: '#7583d1',
                  color: '#fff',
                  whiteSpace: 'nowrap'
                },
              }}
              actions={[
                {
                  icon: 'kill',
                  onClick: (event, rowData: any) => {
                    setOpen(true);
                    setCurrentJob({
                      cluster:rowData['cluster'],
                      jobId: rowData['jobId'],
                      priority:currentJob.priority
                    })
                  }
                },
                {
                  icon: 'Pause',
                  onClick: (event, rowData: any)  => {
                    console.log(rowData);
                  }
                }
              ]}
              components={{
                Action:(props: any) => renderActions(props),

              }}
            />
            <MaterialTable
              title="Unapproved  Jobs"
              columns={[
                {title: 'JobId', field: 'jobId', render: rowData =>  <Link className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link>},
                {title: 'Job Name', field: 'jobName'},
                {title: 'Status', field: 'jobStatus'},
                {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric', customSort: (a: any, b: any) => {
                  return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                }},
                {title: 'Priority', field: 'priority'},
                {title: 'Submitted Time', field: 'jobTime', type: 'date',render: (rowData: any)=>renderDateTime(rowData, 'jobTime')},
                {
                  title: 'Preemptible',
                  field: 'jobParams.preemptionAllowed',
                  type: 'boolean'
                }
              ]}
              data={filterUnApprovedJobs(jobs)}
              options={{
                filtering: false,
                paging: false,
                actionsColumnIndex: -1,
                headerStyle: {
                  backgroundColor: '#7583d1',
                  color: '#fff',
                  whiteSpace: 'nowrap'
                },
                rowStyle: {
                  width:'200',
                }
              }}
              actions={[
                {
                  icon: 'kill',
                  onClick: (event, rowData: any) => {
                    setOpen(true);
                    setCurrentJob({
                      cluster:rowData['cluster'],
                      jobId: rowData['jobId'],
                      priority:currentJob.priority
                    })
                  }
                },
                {
                  icon: 'Pause',
                  onClick: (event, rowData: any)  => {
                    console.log(rowData);
                  }
                }
              ]}
              components={{
                Action: (props: any) => renderActions(props),

              }}
            />
            <MaterialTable
              title="Paused Jobs"
              columns={[
                { title: 'JobId', field: 'jobId', render: rowData =>  <Link className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link> },
                { title: 'Job Name', field: 'jobName'},
                {title:'Status', field:'jobStatus'},
                {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric', customSort: (a: any, b: any) => {
                  return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                } },
                {title: 'Priority', field: 'priority'},
                {title: 'Submitted Time', field: 'jobTime', type: 'date',render: (rowData: any)=>renderDateTime(rowData,'jobTime')},
                {title:'Preemptible', field:'jobParams.preemptionAllowed',type:'boolean'},
                {title:'Finished Time', field:'jobStatusDetail[0].finishedAt',type:'date',emptyValue:'unknown',
                  render: (rowData: any)=>renderDateTime(rowData, 'finishedAt')}
              ]}
              data={filterPauseJobs(jobs)}
              options={{
                filtering: false,
                paging: false,
                actionsColumnIndex: -1,
                headerStyle: {
                  backgroundColor: '#7583d1',
                  color: '#fff',
                  whiteSpace: 'nowrap'
                }
              }}
              actions={[
                {
                  icon: 'kill',
                  onClick: (event, rowData: any) => {
                    setOpen(true);
                    setCurrentJob({
                      cluster:rowData['cluster'],
                      jobId: rowData['jobId'],
                      priority:currentJob.priority
                    })
                  }
                },
                {
                  icon: 'Pause',
                  onClick: (event, rowData: any)  => {
                    console.log(rowData);
                  },
                }
              ]}
              components={{
                Action: (props: any) => renderActions(props) ,

              }}
            />
            <MaterialTable
              title="Finished Jobs"
              columns={[
                { title: 'JobId', field: 'jobId', render: rowData =>  <Link className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link> },
                { title: 'Job Name', field: 'jobName'},
                {title:'Status', field:'jobStatus'},
                {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric', customSort: (a: any, b: any) => {
                  return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                } },
                {title:'Submitted Time', field:'jobTime',type:'date',render: (rowData: any)=>renderDateTime(rowData,'jobTime')},
                {title:'Preemptible', field:'jobParams.preemptionAllowed',type:'boolean'},
                {title:'Finished Time', field:'jobStatusDetail[0].finishedAt',type:'date',emptyValue:'unknown',
                  render: (rowData: any)=>renderDateTime(rowData,'finishedAt'),
                }
              ]}
              data={filterFinishedJobs(jobs)}
              options={{
                filtering: false,
                paging: false,
                actionsColumnIndex: -1,
                headerStyle: {
                  backgroundColor: '#7583d1',
                  color: '#fff',
                  whiteSpace: 'nowrap'
                }
              }}

            />
          </Container>
        </DLTSTabPanel>
        {
          refresh ? allJobs && (Boolean)(_.map(clusters,"admin")[0]) &&
          <DLTSTabPanel value={value} index={1}>
            <Container maxWidth="lg" >
              <JobsSelectByCluster currentCluster={currentCluster} onClusterChange={onClusterChange} clusters={clusters}/>
              <MaterialTable
                title="Running Jobs"
                columns={[
                  {title: 'JobId', field: 'jobId', render: rowData =>  <Link className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link>},
                  {title: 'Job Name', field: 'jobName'},
                  {title: 'Status', field: 'jobStatus'},
                  {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric',
                    customSort: (a: any, b: any) => {
                      return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                    }
                  },
                  {title: 'Username', field: 'userName', render:renderUserName},
                  {title: 'Priority', field: 'priority', render:renderPrioritySet},
                  {title: 'Submitted Time', field: 'jobTime', type: 'date',render: (rowData: any)=>renderDateTime(rowData,'jobTime')},
                  {
                    title: 'Preemptible',
                    field: 'jobParams.preemptionAllowed',
                    type: 'boolean'
                  },
                  {
                    title: 'Started Time',
                    field: 'jobStatusDetail[0].startedAt',
                    type: 'date',
                    emptyValue: 'unknown',
                    render: (rowData: any)=>renderDateTime(rowData,'startedAt')
                  }
                ]}
                data={filterRunningJobs(allJobs)}
                options={{
                  sorting: true,
                  filtering: true,
                  paging: false,
                  actionsColumnIndex: -1,
                  headerStyle: {
                    backgroundColor: '#7583d1',
                    color: '#fff',
                    whiteSpace: 'nowrap'
                  }
                }}
                actions={[
                  {
                    icon: 'kill',
                    onClick: (event, rowData: any) => {
                      setOpen(true);
                      setCurrentJob({
                        cluster:rowData['cluster'],
                        jobId: rowData['jobId'],
                        priority:currentJob.priority
                      })
                    }
                  },
                  {
                    icon: 'Pause',
                    onClick: (event, rowData: any)  => {
                      console.log(rowData);
                    }
                  }
                ]}
                components={{
                  Action: (props: any)=>renderActions(props),
                }}
              />
              <MaterialTable
                title="Queued  Jobs"
                columns={[
                  {title: 'JobId', field: 'jobId', render: rowData =>  <Link  className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link>},
                  {title: 'Job Name', field: 'jobName'},
                  {title: 'Status', field: 'jobStatus'},
                  {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric',
                    customSort: (a: any, b: any) => {
                      return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                    }
                  },
                  {title: 'Username', field: 'userName',render:renderUserName},
                  {title: 'Priority', field: 'priority', render:renderPrioritySet},
                  {title: 'Submitted Time', field: 'jobTime', type: 'date',render: (rowData: any)=>renderDateTime(rowData,'jobTime')},
                  {
                    title: 'Preemptible',
                    field: 'jobParams.preemptionAllowed',
                    type: 'boolean'
                  }
                ]}
                data={filterQueuedJobs(allJobs)}
                options={{
                  filtering: true,
                  paging: false,
                  actionsColumnIndex: -1,
                  headerStyle: {
                    backgroundColor: '#7583d1',
                    color: '#fff',
                    whiteSpace: 'nowrap'
                  }
                }}
                actions={[
                  {
                    icon: 'kill',
                    onClick: (event, rowData: any) => {
                      setOpen(true);
                      setCurrentJob({
                        cluster:rowData['cluster'],
                        jobId: rowData['jobId'],
                        priority:currentJob.priority
                      })
                    }
                  },
                  {
                    icon: 'Approve',
                    onClick: (event, rowData: any)  => {
                      setOpenApprove(true);
                      setCurrentJob({
                        cluster:rowData['cluster'],
                        jobId: rowData['jobId'],
                        priority:currentJob.priority
                      })
                    }
                  },
                  {
                    icon: 'Pause',
                    onClick: (event, rowData: any)  => {
                      console.log(rowData);
                    }
                  }
                ]}
                components={{
                  Action: (props: any)=>renderActions(props),

                }}

              />
              <MaterialTable
                title="Unapproved  Jobs"
                columns={[
                  {title: 'JobId', field: 'jobId', render: rowData =>  <Link className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link>},
                  {title: 'Job Name', field: 'jobName'},
                  {title: 'Status', field: 'jobStatus'},
                  {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric', customSort: (a: any, b: any) => {
                    return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                  }},
                  {title: 'Username', field: 'userName', render:renderUserName},
                  {title: 'Priority', field: 'priority', render:renderPrioritySet},
                  {title: 'Submitted Time', field: 'jobTime', type: 'date',render: (rowData: any)=>renderDateTime(rowData,'jobTime')},
                  {
                    title: 'Preemptible',
                    field: 'jobParams.preemptionAllowed',
                    type: 'boolean'
                  }
                ]}
                data={filterUnApprovedJobs(allJobs)}
                options={{
                  filtering: true,
                  paging: false,
                  actionsColumnIndex: -1,
                  headerStyle: {
                    backgroundColor: '#7583d1',
                    color: '#fff',
                    whiteSpace: 'nowrap'
                  }
                }}
                actions={[
                  {
                    icon: 'kill',
                    onClick: (event, rowData: any) => {
                      setOpen(true);
                      setCurrentJob({
                        cluster:rowData['cluster'],
                        jobId: rowData['jobId'],
                        priority:currentJob.priority
                      })
                    }
                  },
                  {
                    icon: 'Approve',
                    onClick: (event, rowData: any)  => {
                      setOpenApprove(true);
                      setCurrentJob({
                        cluster:rowData['cluster'],
                        jobId: rowData['jobId'],
                        priority:currentJob.priority
                      })
                    }
                  },
                  {
                    icon: 'Pause',
                    onClick: (event, rowData: any)  => {
                      console.log(rowData);
                    }
                  }
                ]}
                components={{
                  Action: (props: any)=>renderActions(props),

                }}
              />
              <MaterialTable
                title="Paused Jobs"
                columns={[
                  { title: 'JobId', field: 'jobId', render: rowData =>  <Link className={classes.linkStyle} to={`/job/${rowData.cluster}/${rowData.jobId}`}>{rowData.jobId}</Link> },
                  { title: 'Job Name', field: 'jobName'},
                  {title:'Status', field:'jobStatus'},
                  {title:'GPU', field:'jobParams.resourcegpu', render: (rowData: any) => <span>{ rowData['jobParams']['jobtrainingtype'] === 'RegularJob' || !rowData['jobParams'].hasOwnProperty('jobtrainingtype')  ? (Number)(rowData.jobParams.resourcegpu) :  (Number)(rowData.jobParams.resourcegpu * rowData.jobParams.numpsworker)  }</span>, type: 'numeric', customSort: (a: any, b: any) => {
                    return a.jobParams.resourcegpu - b.jobParams.resourcegpu || a.jobParams.resourcegpu * a.jobParams.numpsworker - b.jobParams.resourcegpu * b.jobParams.numpsworker
                  } },
                  {title:'Username', field:'userName', render:renderUserName},
                  {title: 'Priority', field: 'priority'},
                  {title: 'Submitted Time', field: 'jobTime', type: 'date',render: (rowData: any)=>renderDateTime(rowData,'jobTime')},
                  {title:'Preemptible', field:'jobParams.preemptionAllowed',type:'boolean'},
                  {title:'Finished Time', field:'jobStatusDetail[0].finishedAt',type:'date',emptyValue:'unknown',
                    render: (rowData: any)=>renderDateTime(rowData, 'finishedAt')},
                ]}
                data={filterPauseJobs(allJobs)}
                options={{
                  filtering: true,
                  paging: false,
                  actionsColumnIndex: -1,
                  headerStyle: {
                    backgroundColor: '#7583d1',
                    color: '#fff',
                    whiteSpace: 'nowrap'
                  }
                }}
                actions={[
                  {
                    icon: 'kill',
                    onClick: (event, rowData: any) => {
                      setOpen(true);
                      setCurrentJob({
                        cluster:rowData['cluster'],
                        jobId: rowData['jobId'],
                        priority:currentJob.priority
                      })
                    }
                  },
                  {
                    icon: 'Pause',
                    onClick: (event, rowData: any)  => {
                    },
                  }
                ]}
                components={{
                  Action: (props: any)=>renderActions(props),

                }}
              />
            </Container>
          </DLTSTabPanel> : <CircularProgress/>
        }
        <DLTSSnackbar message={message}
          openKillWarn={openKillWarn}
          openPauseWarn={openPauseWarn}
          openResumeWarn={openResumeWarn}
          openUpatePriorityWarn={openUpatePriorityWarn}
          openApproveWarn={openApproveWarn}
          handleWarnClose={handleWarnClose}
        />
      </Fragment>
    )
  }
  return (
    <Box display="flex" justifyContent="center">
      <CircularProgress/>
    </Box>
  )
};
export default Jobs;

