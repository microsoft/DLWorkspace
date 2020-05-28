import * as React from 'react';
import {
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
import TeamContext from '../../../contexts/Team';
import UserContext from '../../../contexts/User';
import { formatBytes, formatPercent } from '../../../utils/formats';
import { useCluster } from './Context';

const LIST_ITEM_HEIGHT = 64;

const joinPath = (...paths: string[]) => paths
  .filter(Boolean).map(path => path.replace(/^\/|\/$/g, '')).join('/')

const StorageList: FunctionComponent = () => {
  const { email } = useContext(UserContext);
  const { currentTeamId } = useContext(TeamContext);
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
    if (!containerPath) return;
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
        const ratio = loading ? 0 : 1 - available / size;
        const secondary = (
          <>
            <LinearProgress
              variant="determinate"
              value={ratio * 100}
              color={ratio > .8 ? 'secondary' : 'primary'}
            />
            {
              loading
                ? 'Loading...'
                : `${formatBytes(size - available)} / ${formatBytes(size)} (${formatPercent(ratio, 0)})`
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
