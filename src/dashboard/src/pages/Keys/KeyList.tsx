import * as React from 'react';
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
} from 'react';

import {
  Avatar,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Paper,
  Tooltip,
  Typography,
} from '@material-ui/core';
import {
  Delete,
  VpnKey,
} from '@material-ui/icons';

import { useSnackbar } from 'notistack';

import useFetch from 'use-http-1';

import Loading from '../../components/Loading';
import useConfirm from '../../hooks/useConfirm';
import { formatDateDistance } from '../../utils/formats';

interface KeyList {
  get(): Promise<any>;
}

interface KeyListProps {
  since?: Date;
  onDelete?(id: number): void;
}

const KeyList = forwardRef<KeyList, KeyListProps>(({ since, onDelete }, ref) => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const confirm = useConfirm();
  const { data, error, get } = useFetch('/api/keys', []);

  const keys = useMemo(() => {
    if (data === undefined) return undefined;
    if (!Array.isArray(data)) return undefined;
    if (since === undefined) return data;
    return data.filter(({ added }) => Date.parse(added) >= since.valueOf());
  }, [since, data]);

  const handleDeleteClick = useCallback((id: number, name: string) => () => {
    if (onDelete !== undefined) {
      confirm(`Do you want to delete the SSH key ${name}?`).then((answer) => {
        if (answer) {
          onDelete(id);
        }
      })
    }
  }, [confirm, onDelete]);

  useImperativeHandle(ref, () => ({ get }), [get]);

  useEffect(() => {
    if (error != null) {
      const key = enqueueSnackbar(`Failed to fetch keys: ${error.message}`, {
        variant: 'error'
      });
      if (key != null) {
        return () => { closeSnackbar(key); };
      }
    }
  }, [error, enqueueSnackbar, closeSnackbar]);

  if (keys === undefined) {
    return <Loading>Fetching SSH keys</Loading>;
  }

  if (keys.length === 0) {
    return <Typography variant="body1" align="center">No SSH keys.</Typography>;
  }

  return (
    <List dense disablePadding component={Paper}>
      {
        keys.map(({ id, name, added }) => (
          <ListItem key={id}>
            <ListItemAvatar>
              <Avatar>
                <VpnKey/>
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              primary={name}
              secondary={`Added ${formatDateDistance(new Date(Date.parse(added)))}`}
            />
            { onDelete && (
              <ListItemSecondaryAction>
                <Tooltip title="Delete">
                  <IconButton edge="end" aria-label="delete" onClick={handleDeleteClick(id, name)}>
                    <Delete/>
                  </IconButton>
                </Tooltip>
              </ListItemSecondaryAction>
            ) }
          </ListItem>
        ))
      }
    </List>
  );
});

export default KeyList;
