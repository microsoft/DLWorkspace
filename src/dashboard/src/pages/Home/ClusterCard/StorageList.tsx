import React, {
  FunctionComponent,
  MouseEvent,
  useCallback,
  useContext,
  useMemo
} from 'react';
import {
  Avatar,
  List,
  ListItem,
  ListItemText,
  LinearProgress,
  ListItemAvatar,
  Tooltip,
} from '@material-ui/core';
import { Folder, FolderShared } from '@material-ui/icons';
import { useSnackbar } from 'notistack';
import copy from 'clipboard-copy';

import {
  each,
  endsWith,
  includes,
  get,
  last,
  map,
  set,
  sortBy
} from 'lodash';

import usePrometheus from '../../../hooks/usePrometheus';
import TeamsContext from '../../../contexts/Teams';
import UserContext from '../../../contexts/User';
import { useCluster } from './Context';

const LIST_ITEM_HEIGHT = 64;

const humanBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KiB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MiB`;
  if (bytes < 1024 * 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GiB`;
  return `${(bytes / 1024 / 1024 / 1024 / 1024).toFixed(2)} TiB`;
};

const joinPath = (...paths: string[]) => paths
  .filter(Boolean).map(path => path.replace(/^\/|\/$/g, '')).join('/')

const StorageList: FunctionComponent = () => {
  const { email } = useContext(UserContext);
  const { selectedTeam } = useContext(TeamsContext);
  const { enqueueSnackbar } = useSnackbar();
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
    if (endsWith(mountpoint, '/mntdlws/nfs')) return '~';
    const directories = mountpoint.split('/');
    if (includes(directories, selectedTeam)) {
      return '/' + last(directories);
    }
  }, [selectedTeam]);

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
    if (!containerPath) return;
    if (containerPath === '~') return joinPath(workStorage, userName);
    return joinPath(workStorage, selectedTeam, containerPath);
  }, [workStorage, userName, selectedTeam]);

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

  const handleClick = useCallback((event: MouseEvent<HTMLAnchorElement, unknown>) => {
    event.preventDefault();

    const { href } = event.currentTarget;
    copy(href);
    enqueueSnackbar(<div>{'Copied '}<code>{href}</code>{' to clipboard'}</div>, {
      variant: 'info'
    });
  }, [enqueueSnackbar]);

  return (
    <List
      dense
      disablePadding
      component="div"
      style={{ height: LIST_ITEM_HEIGHT * 2, overflow: 'auto' }}
    >
      { mountpoints.map(({ containerPath, size, available }) => {
        const loading = size == null || available == null;
        const href = getMountpointUrl(containerPath);
        const tooltipTitle = <><code>{href}</code><br/>Click to copy to clipboard</>;
        const primary = <code>{containerPath}</code>;
        const percent = loading ? 0 : 100 - available * 100 / size;
        const secondary = (
          <>
            <LinearProgress
              variant="determinate"
              value={percent}
              color={percent > 80 ? 'secondary' : 'primary'}
            />
            {
              loading
                ? 'Loading...'
                : `${humanBytes(size - available)} / ${humanBytes(size)} (${percent.toFixed(0)}%)`
            }

          </>
        );
        return (
          <Tooltip key={containerPath} title={tooltipTitle}>
            <ListItem button component="a" href={href} onClick={handleClick}>
              <ListItemAvatar>
                <Avatar>
                  { containerPath === '~' ? <FolderShared/> : <Folder/>}
                </Avatar>
              </ListItemAvatar>
              <ListItemText
                primary={primary}
                secondary={secondary}
                secondaryTypographyProps={{ component: 'div' }}
              />
            </ListItem>
          </Tooltip>
        );
      }) }
    </List>
  );
};

export default StorageList;
