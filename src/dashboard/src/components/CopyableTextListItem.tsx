import React, {
  FunctionComponent,
  useCallback
} from 'react';
import {
  ListItem,
  ListItemText
} from '@material-ui/core';
import { useSnackbar } from 'notistack';
import copy from 'clipboard-copy';

interface CopyableTextListItemProps {
  primary: string;
  secondary: string;
}

const CopyableTextListItem: FunctionComponent<CopyableTextListItemProps> = ({ primary, secondary }) => {
  const { enqueueSnackbar } = useSnackbar();
  const onClick = useCallback(() => {
    copy(secondary).then(
      () => enqueueSnackbar(`Copied to clipboard`, { variant: 'success' }),
      () => enqueueSnackbar('Failed to copy text', { variant: 'error' })
    )
  }, [secondary, enqueueSnackbar]);
  return (
    <ListItem button onClick={onClick}>
      <ListItemText primary={primary} secondary={secondary}/>
    </ListItem>
  );
}

export default CopyableTextListItem;
