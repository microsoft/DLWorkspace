import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import useFetch from 'use-http';

import {
  Card,
  CardHeader,
  CardContent,
  Typography,
} from '@material-ui/core';

import Context from './Context';

const Log: React.FC = () => {
  const { clusterId, jobId } = useContext(Context);

  const [log, setLog] = useState<{ [podName: string]: string } | string>({});
  const [cursor, setCursor] = useState<string | null>(null);
  useEffect(() => {
    setLog({});
    setCursor(null);
  }, [clusterId, jobId])

  const { data, error, get } = useFetch('/api');
  const getMore = useCallback(() => {
    let url = `/clusters/${clusterId}/jobs/${jobId}/log`;
    if (cursor != null) {
      url += `?cursor=${cursor}`;
    }
    get(url);
  }, [clusterId, jobId, cursor]);
  useEffect(() => { getMore(); }, [getMore]);

  useEffect(() => {
    if (data != null) {
      const { log: nextLog, cursor } = data;
      if (typeof nextLog == 'string') {
        setLog(nextLog);
        setCursor(cursor);
        return;
      }
      const newLog = Object.assign(Object.create(null), log)
      for (const podName of Object.keys(nextLog)) {
        newLog[podName] = (newLog[podName] || "") + nextLog[podName]
      }
      setLog(newLog);
      setCursor(cursor);
    }
  }, [data])

  const logText = useMemo(() => {
    if (typeof log == 'string') {
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

  const timeout = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    if (error != null) {
      if (timeout.current != null) {
        console.warn('timeout.current is still set');
        clearTimeout(timeout.current);
      }
      timeout.current = setTimeout(getMore, 1000);
    }

    return () => {
      if (timeout.current != null) {
        clearTimeout(timeout.current);
        timeout.current = undefined;
      }
    };
  }, [error, getMore]);

  return (
    <Card>
      <CardHeader title="Console Output"/>
      <CardContent>
        <Typography component='pre' style={{overflow:'auto'}}>{logText}</Typography>
      </CardContent>
    </Card>
  );
};

export default Log;
