import React, {
  FunctionComponent,
  useContext,
} from 'react';
import {
  List,
  ListItem,
  ListItemText
} from '@material-ui/core';
import { get } from 'lodash';

import CopyableTextListItem from '../../../components/CopyableTextListItem';

import ClusterContext from '../ClusterContext';
import { Job } from '../utils';

interface Props {
  job: Job;
}

const DetailPanel: FunctionComponent<Props> = ({ job }) => {
  const { cluster } = useContext(ClusterContext);

  const link = `${window.location.origin}/jobs-v2/${encodeURIComponent(cluster.id)}/${encodeURIComponent(job['jobId'])}`
  const submitted = new Date(get(job, 'jobTime'));
  const started = new Date(get(job, 'jobStatusDetail.0.startedAt'));
  const finished = new Date(get(job, 'jobStatusDetail.0.finishedAt'));

  return (
    <List dense disablePadding>
      <CopyableTextListItem
        primary="Job Link"
        secondary={link}
      />
      { isNaN(submitted.valueOf()) || (
        <ListItem>
          <ListItemText
            primary="Job Submitted Time"
            secondary={submitted.toLocaleString()}
          />
        </ListItem>
      ) }
      { isNaN(started.valueOf()) || (
        <ListItem>
          <ListItemText
            primary="Job Started Time"
            secondary={started.toLocaleString()}
          />
        </ListItem>
      ) }
      { isNaN(finished.valueOf()) || (
        <ListItem>
          <ListItemText
            primary="Job Finished Time"
            secondary={finished.toLocaleString()}
          />
        </ListItem>
      ) }
    </List>
  );
}

export default DetailPanel;
