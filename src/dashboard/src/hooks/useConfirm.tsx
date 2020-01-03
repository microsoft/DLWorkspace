import React, {
  useCallback,
  useState
} from 'react';
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@material-ui/core';

const useConfirm = () => {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState<string>();
  const [resolve, setResolve] = useState<(value: boolean) => void>();
  const confirm = useCallback((message: string) => {
    setMessage(message);
    setOpen(true);
    return new Promise<boolean>((resolve) => {
      setResolve(() => resolve); // To avoid callbackify set-action
    });
  }, [setResolve, setMessage])
  const onNoClick = useCallback(() => {
    setOpen(false);
    if (resolve) resolve(false);
  }, [resolve]);
  const onClose = onNoClick;
  const onYesClick = useCallback(() => {
    setOpen(false);
    if (resolve) resolve(true);
  }, [resolve]);
  const dialog = (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Confirm</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button autoFocus color="primary" onClick={onNoClick}>No</Button>
        <Button onClick={onYesClick}>Yes</Button>
      </DialogActions>
    </Dialog>
  );
  return {
    confirm,
    dialog,
  }
}

export default useConfirm;
