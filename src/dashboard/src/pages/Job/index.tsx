import React, { useCallback } from 'react';
import { RouteComponentProps, withRouter } from 'react-router-dom';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogTitle,
  DialogContent,
  DialogContentText
} from '@material-ui/core';
import Details from './Details';
import useJob from './useJob';

type Job = any;

interface Params {
  clusterId: string;
  jobId: string;
  team: string;
}

const ErrorDialog = withRouter(({ match, history }) => {
  const { clusterId, jobId } = match.params;
  const onClick = useCallback(() => history.push('/jobs'), [history])
  return (
    <Dialog open>
      <DialogTitle>
        Error
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          Failed to fetch the Job {jobId} in Cluster {clusterId}.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClick} color="primary">
          Back
        </Button>
      </DialogActions>
    </Dialog>
  );
});

const Job: React.FC<RouteComponentProps<Params>> = ({ match }) => {
  const { clusterId, jobId,team } = match.params;
  const [job, error] = useJob(clusterId, jobId);

  if (error) return <ErrorDialog/>;
  if (job) return <Details clusterId={clusterId} jobId={jobId} team={team} job={job}/>;

  return (
    <Box display="flex" justifyContent="center">
      <CircularProgress/>
    </Box>
  );
};

export default Job
