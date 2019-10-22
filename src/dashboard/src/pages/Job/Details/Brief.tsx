import React, { useContext } from 'react';
import {
  Card,
  List,
  ListItem,
  ListItemText,
} from '@material-ui/core';

import Context from './Context';
import DoneIcon from "@material-ui/icons/Done";
import ClearIcon from "@material-ui/icons/Clear";
import {green, red} from "@material-ui/core/colors";

const Brief: React.FC = () => {
  const { cluster, job } = useContext(Context);
  return (
    <Card>
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
        <ListItem><ListItemText primary="Job Status" secondary={job['jobStatus']}/></ListItem>
        <ListItem><ListItemText primary="Job Submission Time" secondary={job['jobTime']}/></ListItem>
      </List>
    </Card>
  );
};

export default Brief;
