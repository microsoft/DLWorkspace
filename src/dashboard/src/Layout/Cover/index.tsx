import * as React from 'react'
import {
  FunctionComponent
} from 'react'

import { sample } from 'lodash'

import {
  createStyles,
  makeStyles,
  Box,
  Grid,
  Paper,
  Typography
} from '@material-ui/core'

import image1 from './image1.jpeg'
import image2 from './image2.jpeg'
import image3 from './image3.jpeg'

const useStyles = makeStyles(() => createStyles({
  container: {
    backgroundImage: `url(${sample([image1, image2, image3])})`,
    backgroundSize: 'cover',
    backgroundPosition: 'right'
  }
}))

const Cover: FunctionComponent = ({ children }) => {
  const styles = useStyles()
  return (
    <Grid container justify="flex-end" classes={styles}>
      <Grid
        item xl={4} lg={5} md={6} sm={8} xs={12} zeroMinWidth
        container alignItems="stretch" justify="flex-end"
      >
        <Paper square elevation={6}>
          <Box paddingTop={10} paddingRight={5} paddingBottom={10} paddingLeft={5} minHeight="100%" display="flex">
            <Grid container direction="column" spacing={10} alignItems="center" justify="center">
              <Grid item>
                <Typography variant="h2" component="h1" align="center">
                  Deep Learning Training Service
                </Typography>
              </Grid>
              <Grid item>{children}</Grid>
              <Grid item>
                <Typography variant="body2">
                  {'Built with '}
                  <span role="img" aria-label="heart">❤️</span>
                  {' by Bing DLTS'}
                </Typography>
              </Grid>
            </Grid>
          </Box>
        </Paper>
      </Grid>
    </Grid>
  )
}

export default Cover
