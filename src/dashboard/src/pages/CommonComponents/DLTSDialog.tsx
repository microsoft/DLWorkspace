import * as React from 'react'
import {
  Button, Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle
} from '@material-ui/core'
import { grey } from '@material-ui/core/colors'
import { TransitionProps } from '@material-ui/core/transitions'
import Slide from '@material-ui/core/Slide'

interface DialogProps {
  children?: React.ReactNode;
  open: boolean;
  message: any;
  handleClose: any;
  handleConfirm: any;
  confirmBtnTxt: any;
  cancelBtnTxt: any;
  title: string;
  titleStyle: object;
}
const Transition = React.forwardRef<unknown, TransitionProps & { children?: React.ReactElement }>(function Transition (props, ref) {
  return <Slide direction="down" ref={ref} {...props} />
})
export const DLTSDialog = (props: DialogProps) => {
  const { children, open, message, handleClose, handleConfirm, confirmBtnTxt, cancelBtnTxt, title, titleStyle } = props

  return (
    <Dialog
      open={open}
      TransitionComponent={Transition}
      onClose={handleClose}
    >
      <DialogTitle id="alert-dialog-title" style={titleStyle}>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText id="alert-dialog-description" style={{ color: grey[400] }}>
          {message}
          {children}
        </DialogContentText>
      </DialogContent>
      {
        (cancelBtnTxt || confirmBtnTxt) &&
        <DialogActions>
          <Button onClick={handleClose} color="primary">
            {cancelBtnTxt}
          </Button>
          <Button onClick={handleConfirm} color="secondary" autoFocus>
            {confirmBtnTxt}
          </Button>
        </DialogActions>
      }

    </Dialog>
  )
}
