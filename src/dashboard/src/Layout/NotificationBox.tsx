import * as React from 'react';
import {
  Fragment,
  FunctionComponent,
  useContext,
  useMemo
} from 'react'
import useFetch from 'use-http-1'
import {
  Box,
  BoxProps,
  Divider,
  Paper,
  Typography,
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

const ClusterNotifications: FunctionComponent<{ cluster: any }> = ({ cluster }) => {
  const { data } = useFetch(`/api/clusters/${cluster.id}`, [cluster.id])
  const notifications = useMemo(() => {
    if (data === undefined) return []
    if (!Array.isArray(data.notifications)) return []
    return data.notifications as string[]
  }, [data])
  const paperStyle = usePaperStyle()
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
                paddingLeft={1}
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
  return (
    <Box {...props}>
      {clusters.map(cluster => (
        <ClusterNotifications key={cluster.id} cluster={cluster}/>
      ))}
    </Box>
  );
};

export default NotificationBox;
