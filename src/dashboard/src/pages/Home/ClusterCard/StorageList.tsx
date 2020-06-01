import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useContext,
  useMemo
} from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  ListSubheader,
  LinearProgress,
  Typography,
  createStyles,
  makeStyles,
} from '@material-ui/core';

import {
  each,
  includes,
  get,
  last,
  map,
  set,
  sortBy
} from 'lodash';

import usePrometheus from '../../../hooks/usePrometheus';
import TeamContext from '../../../contexts/Team';
import UserContext from '../../../contexts/User';
import { formatBytes, formatPercent } from '../../../utils/formats';
import { useCluster } from './Context';

const LIST_ITEM_HEIGHT = 48;

const useListStyles = makeStyles(() => createStyles({
  root: {
    height: LIST_ITEM_HEIGHT * 3,
    overflow: 'auto',
  },
}));

const useListSubheaderStyles = makeStyles(() => createStyles({
  root: {
    height: LIST_ITEM_HEIGHT,
    textAlign: 'center',
  }
}));

const useListItemStyles = makeStyles((theme) => createStyles({
  root: {
    height: LIST_ITEM_HEIGHT,
  },
}))

const useLinearProgressStyles = makeStyles((theme) => createStyles({
  root: {
    height: 10,
  },
  bar: {
    backgroundColor: (ratio: number) => {
      if (ratio <= .5) return theme.palette.success.main;
      if (ratio <= .75) return theme.palette.warning.main;
      return theme.palette.error.main;
    }
  },
  colorPrimary: {
    backgroundColor: theme.palette.grey[400],
  },
}));

interface StorageListItemProps {
  containerPath: string;
  sambaPath: string;
  size?: number;
  available?: number;
}

const StorageListItem: FunctionComponent<StorageListItemProps> = ({ containerPath, size, available }) => {
  const ratio = useMemo(() => {
    if (size === undefined) return 0;
    if (available === undefined) return 0;
    return available / size;
  }, [size, available]);
  const listItemStyles = useListItemStyles();
  const linearProgressStyles = useLinearProgressStyles(ratio);

  const primary = (
    <LinearProgress
      variant="determinate"
      value={ratio * 100}
      classes={linearProgressStyles}
    />
  );
  const secondary = (
    <Box display="flex" justifyContent="space-between">
      <Typography variant="caption" color="inherit">{containerPath}</Typography>
      <Typography variant="caption" color="inherit">
        {
          available !== undefined && size !== undefined
            ? `(${formatBytes(available)}/${formatBytes(size)}) ${formatPercent(ratio, 0)} used`
            : 'Loading...'
        }
      </Typography>
    </Box>
  );

  return (
    <ListItem classes={listItemStyles}>
      <ListItemText
        primary={primary}
        secondary={secondary}
        disableTypography
      />
    </ListItem>
  );
}

const joinPath = (...paths: string[]) => paths
  .filter(Boolean).map(path => path.replace(/^\/|\/$/g, '')).join('/')

const StorageList: FunctionComponent = () => {
  const { email } = useContext(UserContext);
  const { currentTeamId } = useContext(TeamContext);
  const { status } = useCluster();

  const grafana = useMemo(() => {
    if (status == null) return;
    if (status.config == null) return;
    return status.config['grafana'];
  }, [status]);
  const size = usePrometheus(grafana, 'node_filesystem_size_bytes{fstype="nfs4"}');
  const available = usePrometheus(grafana, 'node_filesystem_avail_bytes{fstype="nfs4"}');

  const getContainerPath = useCallback((mountpoint: string) => {
    if (!mountpoint) return;
    if (includes(mountpoint, '/mntdlws/nfs')) return '~';
    const directories = mountpoint.split('/');
    if (includes(directories, currentTeamId)) {
      return '/' + last(directories);
    }
  }, [currentTeamId]);

  const workStorage = useMemo(() => {
    if (status == null) return;
    if (status.config == null) return;
    return status.config['workStorage'];
  }, [status]);
  const userName = useMemo(() => {
    if (email == null) return '';
    return email.split('@', 1)[0]
  }, [email]);
  const getMountpointUrl = useCallback((containerPath: string) => {
    if (!containerPath) return joinPath(workStorage);
    if (containerPath === '~') return joinPath(workStorage, userName);
    return joinPath(workStorage, currentTeamId, containerPath);
  }, [workStorage, userName, currentTeamId]);

  const mountpoints = useMemo(() => {
    const mountpointMap = Object.create(null);
    each(get(size, 'result'), ({ metric, value }) => {
      const { mountpoint } = metric;
      const [, size] = value;
      if (mountpoint != null) {
        const containerPath = getContainerPath(mountpoint);
        if (containerPath != null) {
          set(mountpointMap, [containerPath, 'size'], Number(size))
        }
      }
    })
    each(get(available, 'result'), ({ metric, value }) => {
      const { mountpoint } = metric;
      const [, available] = value;
      if (mountpoint != null) {
        const containerMountpoint = getContainerPath(mountpoint);
        if (containerMountpoint != null) {
          set(mountpointMap, [containerMountpoint, 'available'], Number(available))
        }
      }
    })
    return sortBy(map(mountpointMap,
      ({ size, available }, containerPath) => ({ containerPath, size, available })
    ), 'containerPath');
  }, [size, available, getContainerPath]);

  const listStyles = useListStyles();
  const listHeaderStyles = useListSubheaderStyles();

  const subheader = (
    <ListSubheader
      disableSticky
      color="inherit"
      classes={listHeaderStyles}
    >
      <Typography variant="h6" color="inherit">
        {mountpoints.length > 0 ? 'Storages' : 'Loading Storages...'}
      </Typography>
    </ListSubheader>
  );

  return (
    <List
      dense
      disablePadding
      subheader={subheader}
      classes={listStyles}
    >
      { mountpoints.map(({ containerPath, size, available }) => {
        const sambaPath = getMountpointUrl(containerPath);
        return (
          <StorageListItem
            containerPath={containerPath}
            sambaPath={sambaPath}
            size={size}
            available={available}
          />
        );
      }) }
    </List>
  );
};

export default StorageList;
