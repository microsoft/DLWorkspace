import React, { useCallback, useContext, useState, useEffect, useRef } from 'react';

import {
  Card,
  CardHeader,
  CardContent,
  Typography,
} from '@material-ui/core';

import Context from './Context';

const Log: React.FC = () => {
  const { clusterId, jobId } = useContext(Context);
  const [log, setLog] = useState("");
  const [cursor, setCursor] = useState<string>();
  const timeout = useRef<any>();
  const mounted = useRef(false);

  const request = useCallback(async () => {
    const url = new URL(`/api/clusters/${clusterId}/jobs/${jobId}/log`, window.location.href);
    if (cursor != null) {
      url.searchParams.set('cursor', cursor);
    }
    const response = await fetch(url.toString())
    if (!response.ok && mounted.current) {
      timeout.current = setTimeout(request, 1000)
      return;
    }

    const text = await response.text();
    setLog(log + text);

    const link = response.headers.get('link');
    if (link != null) {
      const match = link.match(/\?cursor=(.+?)(?:&|>|$)/);
      if (match != null) {
        setCursor(match[1]);
      }
    }
  }, [clusterId, jobId, cursor]);

  useEffect(() => {
    mounted.current = true;
    request();
    return () => {
      mounted.current = false;
      if (timeout.current) {
        clearTimeout(timeout.current);
      }
    }
  }, [clusterId, jobId, cursor]);

  return (
    <Card>
      <CardHeader title="Console Output"/>
      <CardContent>
        <Typography component='pre' style={{overflow:'auto'}}>{log}</Typography>
      </CardContent>
    </Card>
  );
};

export default Log;
