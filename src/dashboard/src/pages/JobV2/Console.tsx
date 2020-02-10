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
import { mergeWith } from 'lodash';

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
        if (newData === undefined || newData.cursor == null) {
          return currentData;
        }
        if (typeof currentData.log !== typeof newData.log) {
          return newData;
        }
        if (typeof currentData.log === 'string') {
          return {
            log: currentData.log + newData.log,
            cursor: newData.cursor
          };
        }
        return {
          log: mergeWith(currentData.log, newData.log, (a, b) => a + b),
          cursor: newData.cursor
        };
      }
    }, [clusterId, jobId]);

  const log = useMemo<{ [podName: string]: string } | string | undefined>(() => {
    if (data !== undefined) {
      return data.log;
    } else {
      return undefined;
    }
  }, [data]);

  const logText = useMemo(() => {
    if (typeof log !== 'object') {
      return log;
    }
    const logText: string[] = [];
    const podNames = Object.keys(log).sort()
    for (const podName of podNames) {
      logText.push(`
=========================================================
=========================================================
=========================================================
        logs from pod: ${podName}
=========================================================
=========================================================
=========================================================
${log[podName]}
=========================================================
        end of logs from pod: ${podName}
=========================================================


`);
    }
    return logText.join("");
  }, [log]);

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
    if (error.message === 'Not Found') return;

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
        {logText}
      </Box>
    </Box>
  );
}

export default Console;
