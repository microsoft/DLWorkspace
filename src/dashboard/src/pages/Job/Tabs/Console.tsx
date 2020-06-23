import * as React from 'react';
import {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
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
  MenuItem,
  Paper,
  Select,
  Toolbar,
  Typography,
  createMuiTheme,
  useTheme,
} from '@material-ui/core';
import { ThemeProvider } from "@material-ui/styles";
import { useWindowSize } from 'react-use';
import useFetch from 'use-http-1';
import { useSnackbar } from 'notistack';
import { map, mergeWith } from 'lodash';

import Context from '../Context';

import BottomKeepingBox from '../../../components/BottomKeepingBox';
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
  const { job } = useContext(Context);
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { data, loading, error, get, abort } = useFetch(
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

  useEffect(() => {
    if (loading) return;

    const cursor = data && data.cursor;
    if (error == null) {
      const status = job['jobStatus'];
      if (
        status === 'finished'
        || status === 'failed'
        || status === 'killed'
        || status === 'paused'
        || status === 'queued'
        || status === 'scheduling'
      ) return;
    }
    const delay = error || cursor == null ? 3000 : 0;
    const querystring = cursor && `?cursor=${encodeURIComponent(cursor)}`;
    const timeout = setTimeout(get, delay, querystring);
    return () => {
      clearTimeout(timeout);
      abort();
    }
  }, [job, data, loading, error, get, abort]);

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

  return { loading, log };
}

const Console: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const { height: windowHeight } = useWindowSize();
  const theme = useTheme();
  const box = useRef<HTMLElement>(null);
  const { loading, log } = useLogText();
  const [height, setHeight] = useState(0);
  const [podName, setPodName] = useState<string>();
  const logText = useMemo(() => {
    if (typeof log === 'undefined') return log;
    if (typeof log === 'string') return log;
    if (typeof podName === 'undefined') return undefined;
    return log[podName];
  }, [log, podName]);

  const downloadHref = useMemo(() => {
    return `/api/v2/clusters/${clusterId}/jobs/${jobId}/log`;
  }, [clusterId, jobId]);
  const handleSelectChange = useCallback((event: ChangeEvent<{ value: unknown }>) => {
    setPodName(event.target.value as string);
  }, []);

  useEffect(() => {
    if (typeof log === 'object') {
      const podNames = Object.keys(log)
      if (podNames.length > 0) {
        setPodName(podNames[0])
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeof log]);

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
            <BottomKeepingBox height="100%" m={0} p={1}>
              <Typography variant="inherit" component="pre">
                {logText}
              </Typography>
            </BottomKeepingBox>
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
          { podName !== undefined && (
            <>
              Select Pod:&nbsp;
              <Select value={podName} onChange={handleSelectChange}>
                {
                  typeof log === 'object' && map(log, (_, key) => (
                    <MenuItem key={key} value={key}>{key}</MenuItem>
                  ))
                }
              </Select>
            </>
          ) }
          <Box flex={1}/>
          <Button color="inherit" href={downloadHref}>Download Full Job Log</Button>
        </Toolbar>
      </AppBar>
    </Box>
  );
}

Console.displayName = 'Console';

export default Console;
