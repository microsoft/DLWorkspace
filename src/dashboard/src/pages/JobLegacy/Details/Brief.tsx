import React, {Fragment, useCallback, useContext, useState} from 'react';
import {
  Button,
  Card,
  List,
  ListItem,
  ListItemText, SvgIcon, TextField, Tooltip,
} from '@material-ui/core';
import useFetch from 'use-http';

import Context from './Context';
import DoneIcon from "@material-ui/icons/Done";
import ClearIcon from "@material-ui/icons/Clear";
import {green, red} from "@material-ui/core/colors";
import IconButton from "@material-ui/core/IconButton";
import DeleteIcon from '@material-ui/icons/Delete';
import CheckIcon from "@material-ui/icons/Check";
import {JobsOperationDialog} from "../../JobsLegacy/components/JobsOperationDialog";
import {
  SUCESSFULKILLED,
  SUCCESSFULLYPAUSED,
  SUCCESSFULLYRESUMED, SUCCESSFULLYAPPROVED
} from "../../../Constants/WarnConstants";
import {DLTSSnackbar} from "../../CommonComponents/DLTSSnackbar";

interface BriefProps {
  readonly?: boolean;
}

const Brief: React.FC<BriefProps> = ({ readonly = false }) => {
  const { cluster, job, clusterId, jobId } = useContext(Context);

  const isKillable = useCallback((status: string) => (
    status === 'running' ||
    status === 'scheduling' ||
    status === 'queued' ||
    status === 'unapproved' ||
    status === 'pausing' ||
    status === 'paused'
  ), []);
  const isPausable = useCallback((status: string) => (
    status === 'running' ||
    status === 'scheduling' ||
    status === 'queued' ||
    status === 'unapproved' ||
    status === 'pausing'
  ), []);
  const isApproveable =  useCallback((status: string) => (status === 'unapproved'),[]);
  const isResumeable =  useCallback((status: string) => (status === 'paused'), []);
  const api = useFetch('/api');

  const operations = {
    KILLING: 'killing',
    APPROVED: 'approved',
    PAUSING: 'pausing',
    QUEUED: 'queued'
  }
  const actionHandle = useCallback(async (operation: string) => {
    const body = {"status":operation};
    const data = await api.put(`/clusters/${clusterId}/jobs/${jobId}/status`, body);
    return data;
  }, [api, clusterId, jobId]);

  const isPauseDisplay = !readonly && isPausable(job['jobStatus']);
  const isKillDisplay = !readonly && isKillable(job['jobStatus']);
  const isResumeDisplay = !readonly && isResumeable(job['jobStatus']);
  const isApproveDisplay = !readonly && isApproveable(job['jobStatus']);

  const[open, setOpen] = React.useState(false);
  const[openApprove, setOpenApprove] = React.useState(false);
  const[openResumeWarn, setOpenResumeWarn] = React.useState(false);
  const[openPause, setOpenPause] = React.useState(false);
  const[openResume, setOpenResume] = React.useState(false);
  const[openUpdatePriority,setOpenUpdatePriority] = React.useState(false);
  const[openApproveWarn, setOpenApproveWarn] = React.useState(false);
  const[openPauseWarn, setOpenPauseWarn] = React.useState(false);
  const [message,setMessage] = useState('');
  const[openKillWarn, setOpenKillWarn] = React.useState(false);

  const handleClose = () => {
    setOpen(false);
    setOpenApprove(false);
    setOpenPause(false);
    setOpenResume(false);
  }
  const handleKill = useCallback(()=>{
    setOpen(true)
  },[])
  const handlePause = useCallback(()=>{
    setOpenPause(true)
  },[])
  const handleResume = useCallback(()=>{
    setOpenResume(true)
  },[])
  const handleApprove = useCallback(()=>{
    setOpenApprove(true)
  },[])
  const handleWarnClose = () => {
    setOpenKillWarn(false);
    setOpenApproveWarn(false);
    setOpenPauseWarn(false)
    setOpenResumeWarn(false)
  }
  const handleConfirm = useCallback(()=>{
    if (open) {
      actionHandle(operations.KILLING).then((res)=>{
        if (res) {
          setOpenKillWarn(true);
          setOpen(false);
          setMessage(SUCESSFULKILLED);
        } else {
          alert('kill fail');
        }
      })
    } else if (openPause){
      actionHandle(operations.PAUSING).then((res)=>{
        if (res) {
          setOpenKillWarn(true);
          setOpenPause(false);
          setMessage(SUCCESSFULLYPAUSED);
        } else {
          alert("pause fail");
        }
      })
    } else if (openResume) {
      actionHandle(operations.QUEUED).then((res)=>{
        if (res) {
          setOpenResumeWarn(true);
          setOpenResume(false);
          setMessage(SUCCESSFULLYRESUMED);
        } else {
          alert("approve fail")
        }
      })
    } else if (openApprove) {
      actionHandle(operations.APPROVED).then((res)=>{
        if (res) {
          setOpenApproveWarn(true);
          setOpenApprove(false);
          setMessage(SUCCESSFULLYAPPROVED);
        } else {
          alert("resume fail")
        }
      })
    }
  },[actionHandle, open, openApprove, openPause, openResume, operations.APPROVED, operations.KILLING, operations.PAUSING, operations.QUEUED]);
  return (
    <Card>
      <JobsOperationDialog handleClose={handleClose}
        titleStyle={{color:red[200]}}
        title={"Info"}
        handleConfirm={handleConfirm}
        job={job}
        openApprove={openApprove}
        openPause={openPause} openResume={openResume} openUpdatePriority={openUpdatePriority} open={open}
      />
      <List>
        <ListItem><ListItemText primary="Job Id" secondary={job['jobId']}/></ListItem>
        <ListItem><ListItemText primary="Job Name" secondary={job['jobName']}/></ListItem>
        <ListItem><ListItemText primary="Docker Image" secondary={job['jobParams']['image']}/></ListItem>
        <ListItem>
          <ListItemText
            style={{ overflow: 'auto' }}
            primary="Command"
            secondary={job['jobParams']['cmd']}
            secondaryTypographyProps={{ component: 'pre' }}
          />
        </ListItem>
        <ListItem>
          <ListItemText
            primary="Data Path"
            secondary={`${cluster ? cluster['dataStorage'] : ''}/${job['jobParams']['dataPath']}`}
          />
        </ListItem>
        <ListItem>
          <ListItemText
            primary="Work Path"
            secondary={`${cluster ? cluster['dataStorage'] : ''}/${job['jobParams']['workPath']}`}
          />
        </ListItem>
        <ListItem>
          <ListItemText
            primary="Job Path"
            secondary={`${cluster ? cluster['workStorage'] : ''}/${job['jobParams']['jobPath']}`}
          />
        </ListItem>
        <ListItem><ListItemText primary="PreemptionAllowed" secondary={job['jobParams']['preemptionAllowed'] ? <DoneIcon style={{color:green[500]}}></DoneIcon> : <ClearIcon  style={{color:red[500]}}></ClearIcon>}/></ListItem>
        <ListItem><ListItemText primary="Job Type" secondary={job['jobParams']['jobType']}/></ListItem>
        {
          job['jobParams']['jobtrainingtype'] === 'PSDistJob' && <ListItem><ListItemText primary="Number of Nodes" secondary={job['jobParams']['numpsworker']}/></ListItem>
        }
        {
          job['jobParams']['jobtrainingtype'] === 'PSDistJob' && <ListItem><ListItemText primary="Total of GPUS" secondary={job['jobParams']['numpsworker'] * job['jobParams']['resourcegpu']}/></ListItem>
        }
        {
          job['jobParams']['jobtrainingtype'] === 'RegularJob' && <ListItem><ListItemText primary="Number of GPUS" secondary={job['jobParams']['resourcegpu']}/></ListItem>
        }
        <ListItem><ListItemText primary="Job Status" secondary={
          <>
            {job['jobStatus']}
          </>
        }/></ListItem>
        <ListItem><ListItemText primary="Job Submission Time" secondary={job['jobTime']}/></ListItem>
        <ListItem><ListItemText primary="Actions" secondary={
          <>
            {isKillDisplay && <Tooltip title="Kill Job">
              <IconButton color="secondary" size="small" onClick={handleKill}>
                <DeleteIcon />
              </IconButton>
            </Tooltip>}
            {isPauseDisplay && <Tooltip title="Pause Job">
              <IconButton color="secondary" size="small" onClick={handlePause}>
                <SvgIcon>
                  <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/><path d="M0 0h24v24H0z" fill="none"/>
                </SvgIcon>
              </IconButton>
            </Tooltip>}
            {isResumeDisplay &&<Tooltip title="Resume Job">
              <IconButton style={{ color:green[400] }} size="small" onClick={handleResume}>
                <SvgIcon>
                  <path d="M8 5v14l11-7z"/><path d="M0 0h24v24H0z" fill="none"/>
                </SvgIcon>
              </IconButton>
            </Tooltip>}
            {isApproveDisplay && <Tooltip title="Approve Job">
              <IconButton color="primary"  size={"small"} onClick={handleApprove}>
                <CheckIcon />
              </IconButton>
            </Tooltip>}
          </>
        }/></ListItem>
      </List>
      <DLTSSnackbar message={message}
        open = {openKillWarn || openApproveWarn || openPauseWarn || openResumeWarn}
        handleWarnClose={handleWarnClose}
        autoHideDuration={2000}
      />
    </Card>
  );
};

export default Brief;
