import * as React from 'react'

export const handleChangeTab = (event: React.ChangeEvent<{}>, newValue: number,setValue: any,setShowIframe?: any,setRefresh?: any) => {

  if (setShowIframe) {setShowIframe(false)}
  if (window.navigator.userAgent.indexOf('Edge') != -1) {
    if (setRefresh) {setRefresh(false)
      setTimeout(()=>{
        setRefresh(true)
      },500)
    }
  }

  setTimeout(()=>{
    if (setShowIframe) {
      setShowIframe(true)
    }
  },2000)
  setValue(newValue)
}

export const handleChangeIndex = (index: number, setValue: any) => {
  setValue(index)
}
export const checkFinishedJob = (jobStatus: string) => {
  return jobStatus!== 'running' && jobStatus !== 'queued' && jobStatus !== 'unapproved' && jobStatus !== 'scheduling' && jobStatus !== 'pausing' && jobStatus !== 'paused'
}
