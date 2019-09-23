import React from "react";
import {
  createStyles,
  makeStyles,
  Snackbar,
  SnackbarContent,
  Theme
} from "@material-ui/core";
import {green} from "@material-ui/core/colors";


interface SnackbarProps {
  children?: React.ReactNode;
  message: string;
  open: boolean | false;
  autoHideDuration?: number | 1000;
  handleWarnClose?: any;
}
const useStyles = makeStyles((theme: Theme) =>
  createStyles({
    success: {
      backgroundColor: green[600],
    },
  })
);
export const DLTSSnackbar: React.FC<SnackbarProps> = (props: SnackbarProps) => {
  const classes = useStyles();
  let { children, handleWarnClose,autoHideDuration,message,open } = props;

  return (
    <>
      {
        message !== '' && <Snackbar
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
          open={open}
          autoHideDuration={autoHideDuration}
          onClose={handleWarnClose}
          ContentProps={{
            'aria-describedby': 'message-id',
          }}
        >
          <SnackbarContent
            className={classes.success}
            aria-describedby="client-snackbar"
            message={<span id="message-id" >{message}</span>}
          />
        </Snackbar>
      }
    </>
  )
}
