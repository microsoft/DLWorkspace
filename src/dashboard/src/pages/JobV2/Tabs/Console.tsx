import React, {
  FunctionComponent,
  useEffect,
  useMemo
} from 'react';
import {
  Box
} from '@material-ui/core';
import useFetch from 'use-http-2';
import { useSnackbar } from 'notistack';
import { mergeWith } from 'lodash';

import CodeBlock from '../../../components/CodeBlock';
import Loading from '../../../components/Loading';
import useConstant from '../../../hooks/useConstant';

import useRouteParams from '../useRouteParams';

const Console: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { data, loading, error, get } = useFetch(
    `/api/clusters/${clusterId}/jobs/${jobId}/log`, useConstant({
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
          log: mergeWith({}, currentData.log, newData.log, (a, b) => (a || '') + (b || '')),
          cursor: newData.cursor
        };
      }
    }), [clusterId, jobId]);

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
    if (loading) return;

    const cursor = data && data.cursor;
    const delay = error || cursor == null ? 3000 : 0;
    const querystring = cursor && `?cursor=${encodeURIComponent(cursor)}`;
    const timeout = setTimeout(get, delay, querystring);
    return () => {
      clearTimeout(timeout);
    }
  }, [data, loading, error, get]);

  useEffect(() => {
    if (error === undefined) return;
    if (Number(error.name) === 404) return;

    const key = enqueueSnackbar(`Failed to fetch job log: ${clusterId}/${jobId}`, {
      variant: 'error',
      persist: true
    });
    return () => {
      if (key !== null) closeSnackbar(key);
    }
  }, [error, enqueueSnackbar, closeSnackbar, clusterId, jobId]);

  if (logText === undefined) {
    return <Loading/>;
  }

  return (
    <Box p={1} style={{ overflow: 'auto' }}>
      <CodeBlock>
        {logText}
      </CodeBlock>
      {loading && <Loading/>}
    </Box>
  );
}

Console.displayName = 'Console';

export default Console;
