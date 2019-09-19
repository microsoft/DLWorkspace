import React, {Fragment} from "react";
import {
  createStyles,
  makeStyles,
  Snackbar,
  SnackbarContent,
  Theme
} from "@material-ui/core";
import {blue, green, red} from "@material-ui/core/colors";


interface SnackbarProps {
  children?: React.ReactNode;
  message: string;
  openKillWarn?: boolean | false;
  openPauseWarn?: boolean | false;
  openResumeWarn?: boolean | false;
  openUpatePriorityWarn?: boolean | false;
  openApproveWarn?: boolean | false;
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
export const DLTSSnackbar = (props: SnackbarProps) => {
  const classes = useStyles();
  const { children,handleWarnClose,autoHideDuration,message,openKillWarn,openResumeWarn,openApproveWarn,openPauseWarn,openUpatePriorityWarn } = props;
  let open = openKillWarn || openApproveWarn || openPauseWarn || openResumeWarn || openUpatePriorityWarn;
  if (open === undefined) {
    open = false;
  }
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
