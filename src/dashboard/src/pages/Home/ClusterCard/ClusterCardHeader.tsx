import React, {
  FunctionComponent,
  useCallback,
  useMemo,
  useRef,
  useState
} from 'react';

import { Link } from 'react-router-dom';

import {
  CardHeader,
  IconButton,
  Menu,
  MenuItem
} from '@material-ui/core';
import {
  MoreVert
} from '@material-ui/icons';

import { useCluster } from './Context';

const ActionIconButton: FunctionComponent = () => {
  const { id } = useCluster();

  const [open, setOpen] = useState(false);

  const iconButton = useRef<never>(null);

  const handleIconButtonClick = useCallback(() => setOpen(true), [setOpen]);
  const handleMenuClose = useCallback(() => setOpen(false), [setOpen]);

  return (
    <>
      <IconButton ref={iconButton} onClick={handleIconButtonClick}>
        <MoreVert/>
      </IconButton>
      <Menu
        anchorEl={iconButton.current}
        anchorOrigin={{ horizontal: "right", vertical: "top" }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        open={open}
        onClose={handleMenuClose}
      >
        <MenuItem component={Link} to={`/jobs/${id}`}>View Jobs</MenuItem>
        <MenuItem component={Link} to={`/clusters/${id}`}>Cluster Status</MenuItem>
      </Menu>
    </>
  )
}

const ClusterCardHeader: FunctionComponent = () => {
  const { id, status } = useCluster();

  const subheader = useMemo(() => (
    status && typeof status['runningJobs'] === 'number'
      ? `${status['runningJobs']} Job${status['runningJobs'] !== 1 ? 's' : ''} Running`
      : 'Loading'
  ), [status]);

  return (
    <CardHeader
      title={id}
      titleTypographyProps={{ component: 'h3', variant: 'body2' }}
      subheader={subheader}
      subheaderTypographyProps={{ variant: 'body2' }}
      action={<ActionIconButton/>}
    />
  );
};

export default ClusterCardHeader;
