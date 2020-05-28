import * as React from 'react';
import {CSSProperties} from "react";
import {
  createStyles,
  makeStyles,
  Snackbar,
  SnackbarContent,
  Theme
} from "@material-ui/core";
import {green} from "@material-ui/core/colors";


interface SnackbarProps {
  message: string;
  open: boolean | false;
  autoHideDuration?: number | 1000;
  handleWarnClose?: any;
  style?: CSSProperties;
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
  let { handleWarnClose, autoHideDuration, message, open, style } = props;
  const ogStyle = {};
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
            style={style ? style : ogStyle}
            aria-describedby="client-snackbar"
            message={<span id="message-id" >{message}</span>}
          />
        </Snackbar>
      }
    </>
  )
}
