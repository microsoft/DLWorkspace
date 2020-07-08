import * as React from 'react'
import {
  FunctionComponent
} from 'react'

import {
  Box,
  Typography
} from '@material-ui/core'

interface Props {
  caption?: string;
}

const ColumnTitle: FunctionComponent<Props> = ({ caption, children }) => (
  <Box>
    {children && <Typography variant="inherit" component="p">{children}</Typography>}
    {caption && <Typography variant="caption" component="p">{caption}</Typography>}
  </Box>
)

export default ColumnTitle
