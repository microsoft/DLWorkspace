import * as React from 'react';
import {
  FunctionComponent,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  AppBar,
  Box,
  Button,
  Fade,
  LinearProgress,
  Paper,
  Toolbar,
  Typography,
  createMuiTheme,
  useTheme,
} from '@material-ui/core';
import { ThemeProvider } from "@material-ui/styles";
import { useWindowSize } from 'react-use';
import useFetch from 'use-http-2';
import { useSnackbar } from 'notistack';
import { mergeWith } from 'lodash';

import useConstant from '../../../hooks/useConstant';

import useRouteParams from '../useRouteParams';

const logTheme = createMuiTheme({
  palette: {
    type: 'dark'
  },
  typography: {
    fontFamily: `"Roboto-mono", "Menlo", "Consolas", monospace`
  }
});

const useLogText = () => {
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

  return { loading, logText };
}

const Console: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const { height: windowHeight } = useWindowSize();
  const theme = useTheme();
  const box = useRef<HTMLElement>(null);
  const { loading, logText } = useLogText();
  const [height, setHeight] = useState(0);

  const downloadHref = useMemo(() => {
    return `/api/v2/clusters/${clusterId}/jobs/${jobId}/log`;
  }, [clusterId, jobId]);

  useLayoutEffect(() => {
    if (box.current == null) return;
    const { top } = box.current.getBoundingClientRect();
    const height = windowHeight - top - theme.spacing(3);
    setHeight(height);
  }, [windowHeight, theme]);

  return (
    <Box
      // eslint-disable-next-line @typescript-eslint/ban-ts-ignore
      // @ts-ignore: https://github.com/mui-org/material-ui/issues/17010
      ref={box}
      height={height}
      display="flex"
      flexDirection="column"
    >
      <Box position="relative" height={0} flex={1}>
        <ThemeProvider theme={logTheme}>
          <Box position="absolute" width="100%">
            <Fade in={loading}><LinearProgress/></Fade>
          </Box>
          <Paper square elevation={0} style={{ height: '100%' }}>
            <Box height="100%" m={0} p={1} overflow="auto">
              <Typography variant="inherit" component="pre">
                {logText}
              </Typography>
            </Box>
          </Paper>
        </ThemeProvider>
      </Box>
      <AppBar
        component="footer"
        position="static"
        color="default"
        elevation={0}
      >
        <Toolbar variant="dense">
          <Box flex={1}/>
          <Button color="inherit" href={downloadHref}>Download</Button>
        </Toolbar>
      </AppBar>
    </Box>
  );
}

Console.displayName = 'Console';

export default Console;
