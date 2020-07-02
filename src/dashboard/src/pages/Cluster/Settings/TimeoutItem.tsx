import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { useParams } from 'react-router-dom';

import {
  Button,
  Dialog,
  DialogContent,
  DialogActions,
  DialogTitle,
  FormControlLabel,
  Input,
  InputAdornment,
  Radio,
  RadioGroup,
} from '@material-ui/core';
import { Timer } from '@material-ui/icons';

import { useSnackbar } from 'notistack';

import useFetch from 'use-http-1';

import TeamContext from '../../../contexts/Team';

import SettingItem from './SettingItem';
import Context from './Context';

const TimeoutItem: FunctionComponent<{ value: number | null | undefined }> = ({ value }) => {
  const { clusterId } = useParams();
  const { enqueueSnackbar } = useSnackbar();
  const { getMeta } = useContext(Context);
  const { currentTeamId } = useContext(TeamContext);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogSaveDisabled, setDialogSaveDisabled] = useState(false);
  const [dialogValue, setDialogValue] = useState<number | null>();
  const inputRef = useRef<HTMLInputElement>();

  const text = useMemo(() => {
    if (value === undefined) return undefined;
    if (value === null) return 'Disabled';
    const valueAsHours = value / 60 / 60;
    return `${valueAsHours} ${valueAsHours > 1 ? 'hours' : 'hour'}`;
  }, [value]);

  const { response, error, patch, abort } = useFetch(`/api/v2/clusters/${clusterId}/teams/${currentTeamId}/meta`, {
    headers: {
      'Content-Type': 'application/json'
    }
  })

  const handleItemConfigure = useCallback(() => {
    setDialogOpen(true);
    setDialogValue(value);
  }, [setDialogOpen, value]);
  const handleDialogSave = useCallback(() => {
    if (!(dialogValue === null || (typeof dialogValue === 'number' && dialogValue > 0))) {
      enqueueSnackbar('Invalid timeout value.', { variant: 'error' });
    }
    setDialogSaveDisabled(true);
    patch({
      timeout: dialogValue
    }).then(() => {
      if (response.ok) {
        setDialogOpen(false);
        getMeta();
      }
      setDialogSaveDisabled(false);
    }, () => {
      setDialogSaveDisabled(false);
    });
  }, [dialogValue, enqueueSnackbar, getMeta, patch, response]);
  const handleDialogCancel = useCallback(() => {
    abort();
    setDialogOpen(false);
  }, [abort, setDialogOpen]);
  const handleRadioChange = useCallback((event: unknown, value: string) => {
    setDialogValue(value === 'true' ? 3600 : null);
  }, []);
  const handleTextFieldChange = useCallback(() => {
    if (inputRef.current && Number.isFinite(inputRef.current.valueAsNumber)) {
      setDialogValue(inputRef.current.valueAsNumber * 3600);
    }
  }, []);

  useEffect(() => {
    if (dialogValue !== null && inputRef.current) {
      inputRef.current.focus();
    }
  }, [dialogValue]);
  useEffect(() => {
    if (error) {
      enqueueSnackbar(`Failed to set timeout: ${error.message}`, { variant: 'error' });
    }
  }, [error, enqueueSnackbar]);

  return (
    <>
      <SettingItem
        Icon={Timer}
        name="Timeout"
        text={text}
        onConfigure={handleItemConfigure}
      />
      <Dialog
        maxWidth="xs"
        fullWidth
        open={dialogOpen}
        onClose={handleDialogCancel}
      >
        <DialogTitle>Timeout</DialogTitle>
        <DialogContent>
          <RadioGroup value={String(dialogValue !== null)} onChange={handleRadioChange}>
            <FormControlLabel value="false" control={<Radio />} label="Disable"/>
            <FormControlLabel value="true" control={<Radio />} label="Enable"/>
            <Input
              inputRef={inputRef}
              type="number"
              value={typeof dialogValue === 'number' ? Math.floor(dialogValue / 3600) : ''}
              inputProps={{ min: 1 }}
              disabled={dialogValue === null}
              endAdornment={
                <InputAdornment position="end">
                  {dialogValue == null || dialogValue > 3600 ? 'hours' : 'hour'}
                </InputAdornment>
              }
              onChange={handleTextFieldChange}
            />
          </RadioGroup>
        </DialogContent>
        <DialogActions>
          <Button color="primary" onClick={handleDialogCancel}>Cancel</Button>
          <Button color="primary" disabled={dialogSaveDisabled} onClick={handleDialogSave}>Save</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default TimeoutItem;
