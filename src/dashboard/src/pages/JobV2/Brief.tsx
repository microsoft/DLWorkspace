import React, {
  FunctionComponent,
  useContext
} from 'react';
import {
  List,
  ListItem,
  ListItemText
} from '@material-ui/core';
import {
  Check,
  Close
} from '@material-ui/icons';

import CopyableTextListItem from '../../components/CopyableTextListItem';
import JobStatus from '../../components/JobStatus';

import Context from './Context';

const Brief: FunctionComponent = () => {
  const { cluster, job } = useContext(Context);

  return (
    <List dense>
      <ListItem>
        <ListItemText primary="Job Id" secondary={job['jobId']}/>
      </ListItem>
      <ListItem>
        <ListItemText primary="Job Name" secondary={job['jobName']}/>
      </ListItem>
      <ListItem>
        <ListItemText primary="Team Name" secondary={job['vcName']}/>
      </ListItem>
      <ListItem>
        <ListItemText primary="Docker Image" secondary={job['jobParams']['image']}/>
      </ListItem>
      <ListItem>
        <ListItemText
          primary="Command"
          secondary={job['jobParams']['cmd']}
          secondaryTypographyProps={{ component: 'pre' }}
        />
      </ListItem>
      <CopyableTextListItem
        primary="Data Path"
        secondary={`${cluster['dataStorage'] || ''}/${job['jobParams']['dataPath']}`}
      />
      <CopyableTextListItem
        primary="Work Path"
        secondary={`${cluster['workStorage'] || ''}/${job['jobParams']['workPath']}`}
      />
      <CopyableTextListItem
        primary="Job Path"
        secondary={`${cluster['workStorage'] || ''}/${job['jobParams']['jobPath']}`}
      />
      <ListItem>
        <ListItemText
          primary="Preemptible"
          secondary={job['jobParams']['preemptionAllowed'] ? <Check/> : <Close/>}
        />
      </ListItem>
      {
        job['jobParams']['jobtrainingtype'] === 'PSDistJob' && (
          <ListItem>
            <ListItemText
              primary="Number of Nodes"
              secondary={job['jobParams']['numpsworker']}
            />
          </ListItem>
        )
      }
      {
        job['jobParams']['jobtrainingtype'] === 'PSDistJob' && (
          <ListItem>
            <ListItemText
              primary="Total of GPUs"
              secondary={job['jobParams']['numpsworker'] * job['jobParams']['resourcegpu']}
            />
          </ListItem>
        )
      }
      {
        job['jobParams']['jobtrainingtype'] === 'RegularJob' && (
          <ListItem>
            <ListItemText
              primary="Number of GPUS"
              secondary={job['jobParams']['resourcegpu']}
            />
          </ListItem>
        )
      }
      <ListItem>
        <ListItemText
          primary="Job Status"
          secondary={<JobStatus job={job}/>}
          secondaryTypographyProps={{ component: 'div' }}
        />
      </ListItem>
      <ListItem>
        <ListItemText
          primary="Job Submission Time"
          secondary={new Date(job['jobTime']).toLocaleString()}
        />
      </ListItem>
    </List>
  );
};

export default Brief;
