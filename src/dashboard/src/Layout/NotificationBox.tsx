import * as React from 'react';
import {
  Fragment,
  FunctionComponent,
  useContext,
  useState,
  useMemo
} from 'react'
import useFetch from 'use-http-1'
import {
  Box,
  BoxProps,
  Divider,
  Link,
  Grid,
  Paper,
  Typography,
  Tooltip,
  createStyles,
  makeStyles
} from '@material-ui/core'
import { Info } from '@material-ui/icons'

import ClustersContext from '../contexts/Clusters'

const usePaperStyle = makeStyles(theme => createStyles({
  root: {
    display: 'flex',
    alignItems: 'center',
    padding: theme.spacing(1),
  },
}));

const ClusterNotificationBox: FunctionComponent<{ cluster: any, setAmlLink: any}> = ({ cluster, setAmlLink }) => {
  const { data } = useFetch(`/api/clusters/${cluster.id}`, [cluster.id])
  const notifications = useMemo(() => {
    if (data === undefined) return []
    if (!Array.isArray(data.notifications)) return []
    if (data.amlPortal !== undefined) setAmlLink(data.amlPortal)
    return data.notifications as string[]
  }, [data, setAmlLink])

  const paperStyle = usePaperStyle();

  if (data === undefined) return null

  return (
    <>
      {
        notifications.map((notification, index) => (
          <Fragment key={index}>
            <Paper elevation={0} classes={paperStyle}>
              <Info fontSize="small" color="primary"/>
              <Typography
                variant="body2"
                component={Box}
                flex={1}
                paddingRight={1}
                dangerouslySetInnerHTML={{ __html: notification }}
              />
            </Paper>
            <Divider/>
          </Fragment>
        ))
      }
    </>
  )
}

const NotificationBox: FunctionComponent<BoxProps> = (props) => {
  const { clusters } = useContext(ClustersContext)
  const [amlLink, setAmlLink] = useState(undefined)
  return (
    <Box {...props}>
      {clusters.map(cluster => (
        <ClusterNotificationBox key={cluster.id} cluster={cluster} setAmlLink={setAmlLink}/>
      ))}
      {amlLink
        ? <Grid item xs={12} container justify="flex-end">
          <Info fontSize="small" color="primary"/>
          <Tooltip title="New experimental features. Global job scheduler enables running job on underutilized GPU capacity from other teams. Elastic training enables running a training job in a fault-tolernat and elastic manner.">
            <Link href={amlLink} target="_blank" underline='none'>Try global job scheduler and elastic training</Link>
          </Tooltip>
        </Grid> : null
      }
    </Box>
  );
};

export default NotificationBox;
