import * as React from 'react'
import {

  CircularProgress
} from '@material-ui/core'

import Iframe from 'react-iframe'

interface ClusterUsageType {
  showIframe: boolean;
  iframeUrl: string;
}

export const ClusterUsage = (props: ClusterUsageType) => {
  const {showIframe, iframeUrl} = props
  if (showIframe) {
    return (<Iframe url={iframeUrl} width="100%" height="400"/>)

  } else  {
    return (
      <CircularProgress/>
    )
  }


}
