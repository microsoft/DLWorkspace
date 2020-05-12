import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useContext,
  useRef,
  useState
} from 'react';

import {
  Button,
  Menu,
  MenuItem,
  Typography,
  createStyles,
  makeStyles,
  ListItemIcon
} from '@material-ui/core';
import {
  Check,
  Group
} from '@material-ui/icons';

import TeamsContext from '../../contexts/Teams';

const useButtonStyles = makeStyles(() => createStyles({
  root: {
    textTransform: 'inherit'
  }
}))

const TeamMenuButton: FunctionComponent = () => {
  const { teams, saveSelectedTeam, selectedTeam } = useContext(TeamsContext);

  const [open, setOpen] = useState(false);

  const button = useRef<any>(null);

  const buttonStyles = useButtonStyles();

  const handleButtonClick = useCallback(() => setOpen(true), [setOpen]);
  const handleMenuClose = useCallback(() => setOpen(false), [setOpen]);
  const handleMenuItemClick = useCallback(team => () => {
    saveSelectedTeam(team);
    setOpen(false);
  }, [saveSelectedTeam, setOpen]);

  if (teams == null) return null;
  if (teams.length === 0) return null;

  return (
    <>
      <Button
        ref={button}
        variant="outlined"
        color="inherit"
        classes={buttonStyles}
        startIcon={<Group/>}
        onClick={handleButtonClick}
      >
        {selectedTeam}
      </Button>
      <Menu anchorEl={button.current} open={open} onClose={handleMenuClose}>
        {teams.map(({ id }: { id: string }) => (
          <MenuItem
            key={id}
            disabled={id === selectedTeam}
            onClick={handleMenuItemClick(id)}
          >
            <ListItemIcon>
              {id === selectedTeam ? <Check/> : <Group/>}
            </ListItemIcon>
            <Typography variant="inherit">{id}</Typography>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

export default TeamMenuButton;
