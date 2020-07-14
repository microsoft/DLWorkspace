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
import { get, values } from 'lodash';

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
import { LastPage } from '@material-ui/icons';

import { useSnackbar } from 'notistack';

import useFetch from 'use-http-1';

import TeamContext from '../../../contexts/Team';

import SettingItem from './SettingItem';
import Context from './Context';

const InteractiveGpuItem: FunctionComponent<{ value: number | null | undefined }> = ({ value }) => {
  const { clusterId } = useParams();
  const { enqueueSnackbar } = useSnackbar();
  const { data, getMeta } = useContext(Context);
  const { currentTeamId } = useContext(TeamContext);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogSaveDisabled, setDialogSaveDisabled] = useState(false);
  const [dialogValue, setDialogValue] = useState<number | null>();
  const inputRef = useRef<HTMLInputElement>();

  const totalGpus = useMemo(() => {
    let totalGpus = 0;
    for (const { gpu } of values(get(data, ['types']))) {
      totalGpus += get(gpu, 'total', 0);
    }
    return totalGpus;
  }, [data]);

  const text = useMemo(() => {
    if (value === undefined) return undefined;
    if (value === null) return 'Disabled';
    return `${value} of ${totalGpus} GPU${value > 1 ? 's are' : ' is'} able to be used in interactive (SSH / iPython) jobs.`;
  }, [value, totalGpus]);

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
    if (!(dialogValue === null || (typeof dialogValue === 'number' && dialogValue >= 0))) {
      enqueueSnackbar('Invalid interactive gpu value.', { variant: 'error' });
    }
    setDialogSaveDisabled(true);
    patch({
      interactiveGpu: dialogValue
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
    setDialogValue(value === 'true' ? totalGpus : null);
  }, [totalGpus]);
  const handleTextFieldChange = useCallback(() => {
    if (inputRef.current && Number.isFinite(inputRef.current.valueAsNumber)) {
      setDialogValue(inputRef.current.valueAsNumber);
    }
  }, []);

  useEffect(() => {
    if (dialogValue !== null && inputRef.current) {
      inputRef.current.focus();
    }
  }, [dialogValue]);
  useEffect(() => {
    if (error) {
      enqueueSnackbar(`Failed to set interactive GPU: ${error.message}`, { variant: 'error' });
    }
  }, [error, enqueueSnackbar]);

  return (
    <>
      <SettingItem
        Icon={LastPage}
        name="Interactive GPUs"
        text={text}
        onConfigure={handleItemConfigure}
      />
      <Dialog maxWidth="xs" fullWidth open={dialogOpen} onClose={handleDialogCancel}>
        <DialogTitle>Interactive GPUs</DialogTitle>
        <DialogContent>
          <RadioGroup value={String(dialogValue !== null)} onChange={handleRadioChange}>
            <FormControlLabel value="false" control={<Radio />} label="Disable"/>
            <FormControlLabel value="true" control={<Radio />} label="Enable"/>
            <Input
              inputRef={inputRef}
              type="number"
              value={typeof dialogValue === 'number' ? dialogValue : ''}
              inputProps={{ min: 0, max: totalGpus }}
              disabled={dialogValue === null}
              endAdornment={
                <InputAdornment position="end">
                  {` of ${totalGpus} GPU${totalGpus > 1 ? 's' : ''}`}
                </InputAdornment>
              }
              onChange={handleTextFieldChange}
            />
          </RadioGroup>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogCancel} color="primary">Cancel</Button>
          <Button onClick={handleDialogSave} color="primary" disabled={dialogSaveDisabled}>Save</Button>
        </DialogActions>
      </Dialog>
    </>
  )
};

export default InteractiveGpuItem;
