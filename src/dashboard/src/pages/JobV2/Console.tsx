import React, {
  FunctionComponent,
  useEffect,
  useMemo
} from 'react';
import {
  Box
} from '@material-ui/core';
import { useParams } from 'react-router-dom';
import useFetch from 'use-http-2';
import { useSnackbar } from 'notistack';

import Loading from '../../components/Loading';

interface RouteParams {
  clusterId: string;
  jobId: string;
}

const Console: FunctionComponent = () => {
  const { clusterId, jobId } = useParams<RouteParams>();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { error, data, get } = useFetch(
    `/api/clusters/${clusterId}/jobs/${jobId}/log`, {
      onNewData (currentData, newData) {
        if (currentData === undefined || currentData.cursor == null) {
          return newData;
        }
        return {
          log: currentData.log + newData.log,
          cursor: newData.cursor
        };
      }
    }, [clusterId, jobId]);

  const log = useMemo<string | undefined>(() => {
    if (data !== undefined) {
      return data.log;
    } else {
      return undefined;
    }
  }, [data]);

  useEffect(() => {
    if (data === undefined) return;

    const cursor = data.cursor;
    const timeout = setTimeout(get, 3000,
      cursor ? `?cursor=${encodeURIComponent(cursor)}` : '');
    return () => {
      clearTimeout(timeout);
    }
  }, [data, get]);

  useEffect(() => {
    if (error === undefined) return;

    const key = enqueueSnackbar(`Failed to fetch job log: ${clusterId}/${jobId}`, {
      variant: 'error',
      persist: true
    });
    return () => {
      if (key !== null) closeSnackbar(key);
    }
  }, [error, enqueueSnackbar, closeSnackbar, clusterId, jobId]);

  if (log === undefined) {
    return <Loading/>;
  }

  return (
    <Box p={1} style={{ overflow: 'auto' }}>
      <Box m={0} component="pre">
        {log}
      </Box>
    </Box>
  );
}

export default Console;
