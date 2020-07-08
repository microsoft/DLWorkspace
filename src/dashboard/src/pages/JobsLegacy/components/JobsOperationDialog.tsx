import * as React from 'react'
import { DLTSDialog } from '../../CommonComponents/DLTSDialog'


interface DialogProps {
  children?: React.ReactNode;
  handleClose: any;
  handleConfirm: any;
  job: any;
  openApprove: boolean;
  openPause: boolean;
  openResume: boolean;
  openUpdatePriority: boolean;
  open: boolean;
  title: string;
  titleStyle: object;
}
export const JobsOperationDialog = (props: DialogProps) => {
  const { job, open, handleClose, handleConfirm, openApprove, openPause, openResume, openUpdatePriority, title, titleStyle } = props
  let message = ''
  if (openApprove) {
    message = `${job.jobId} will be approved soon`
  } else if (openPause) {
    message = `${job.jobId} will be paused soon`
  } else if (openResume) {
    message = `${job.jobId} will be resumed soon`
  } else if (open) {
    message = `${job.jobId} will be killed soon`
  } else if (openUpdatePriority) {
    message = `${job.jobId}'s priority will be updated soon`
  }
  if (message === '') {
    return null
  }
  let finalOpen = open || openApprove || openPause || openResume || openUpdatePriority
  return (
    <DLTSDialog
      titleStyle={titleStyle}
      title={title}
      open={finalOpen}
      message={message}
      handleClose={handleClose}
      handleConfirm={handleConfirm}
      confirmBtnTxt={'Yes'} cancelBtnTxt={'No'}/>
  )
}
