import React, {
  useCallback,
  useState
} from 'react';
import {
  Snackbar
} from '@material-ui/core';

const useAlert = () => {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState<string>();
  const [resolve, setResolve] = useState<() => void>();
  const alert = useCallback((message: string) => {
    setOpen(true);
    setMessage(message);
    return new Promise<void>(resolve => {
      setResolve(() => resolve); // To avoid callbackify set-action
    })
  }, []);
  const onClose = useCallback(() => {
    setOpen(false);
    if (resolve !== undefined) resolve();
  }, [resolve]);

  const snackbar = (
    <Snackbar
      open={open}
      message={message}
      autoHideDuration={3000}
      onClose={onClose}
    />
  );

  return {
    alert,
    snackbar
  }
}

export default useAlert;
