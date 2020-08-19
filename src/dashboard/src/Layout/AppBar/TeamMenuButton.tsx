import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useContext,
  useRef,
  useState
} from 'react';

import { sortBy } from 'lodash'

import {
  Button,
  Menu,
  MenuItem,
  Typography,
  Tooltip,
  createStyles,
  makeStyles,
  ListItemIcon
} from '@material-ui/core';
import {
  Check,
  Group
} from '@material-ui/icons';

import TeamContext from '../../contexts/Team';

const useButtonStyles = makeStyles(() => createStyles({
  root: {
    textTransform: 'inherit'
  }
}))

const TeamMenuButton: FunctionComponent = () => {
  const { teams, setCurrentTeamId, currentTeamId } = useContext(TeamContext);

  const [open, setOpen] = useState(false);

  const button = useRef<any>(null);

  const buttonStyles = useButtonStyles();

  const handleButtonClick = useCallback(() => setOpen(true), [setOpen]);
  const handleMenuClose = useCallback(() => setOpen(false), [setOpen]);
  const handleMenuItemClick = useCallback((teamId: string) => () => {
    setCurrentTeamId(teamId);
    setOpen(false);
  }, [setCurrentTeamId, setOpen]);

  if (teams == null) return null;
  if (teams.length === 0) return null;

  return (
    <>
      <Tooltip title="If you cannot see the vc you are authorized, please logout then login." placement="bottom">
        <Button
          ref={button}
          variant="outlined"
          color="inherit"
          classes={buttonStyles}
          startIcon={<Group/>}
          onClick={handleButtonClick}
        >
          {currentTeamId}
        </Button>
      </Tooltip>
      <Menu anchorEl={button.current} open={open} onClose={handleMenuClose}>
        {sortBy(teams, 'id').map(({ id }: { id: string }) => (
          <MenuItem
            key={id}
            disabled={id === currentTeamId}
            onClick={handleMenuItemClick(id)}
          >
            <ListItemIcon>
              {id === currentTeamId ? <Check/> : <Group/>}
            </ListItemIcon>
            <Typography variant="inherit">{id}</Typography>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

export default TeamMenuButton;
