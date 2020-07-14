import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useEffect,
  useMemo
} from 'react'

import { usePreviousDistinct } from 'react-use'
import { useFetch } from 'use-http-1'

import {
  Backdrop,
  Button,
  Card,
  CardActionArea,
  CardMedia,
  CircularProgress,
  Grid,
  Typography,
  createStyles,
  makeStyles
} from '@material-ui/core'

import { useSnackbar } from 'notistack'

import useRouteParams from '../../useRouteParams'

import ipythonIcon from './ipython.svg'
import tensorboardIcon from './tensorboard.svg'
import theiaIcon from './theia.svg'
import portIcon from './port.svg'

const useCardMediaStyles = makeStyles(() => createStyles({
  root: {
    width: 128,
    height: 128
  }
}))

const useBackdropStyles = makeStyles(() => createStyles({
  root: {
    position: 'absolute',
    zIndex: 0,
    color: '#fff'
  }
}))

interface AppProps {
  name?: string
  endpoint?: { [key: string]: any }
}

const App: FunctionComponent<AppProps> = ({ name, endpoint }) => {
  const { clusterId, jobId } = useRouteParams()
  const { response, post } = useFetch(`/api/clusters/${clusterId}/jobs/${jobId}/endpoints`)
  const { enqueueSnackbar } = useSnackbar()

  const icon = useMemo(() => {
    if (name === 'ipython') return ipythonIcon
    if (name === 'tensorboard') return tensorboardIcon
    if (name === 'theia') return theiaIcon
    return portIcon
  }, [name])
  const title = useMemo(() => {
    if (name === 'ipython') return 'Jupyter Notebook'
    if (name === 'tensorboard') return 'TensorBoard'
    if (name === 'theia') return 'VSCode in DLTS'
    if (endpoint === undefined) return 'Expose a Port'
    return String(endpoint['name'])
  }, [name, endpoint])
  const status = useMemo(() => {
    if (endpoint === undefined) return 'not-installed' as const
    if (endpoint['port'] === undefined) return 'installing' as const
    return 'installed' as const
  }, [endpoint])
  const href = useMemo(() => {
    if (endpoint === undefined) return
    return `http://${String(endpoint['nodeName'])}.${String(endpoint['domain'])}:${String(endpoint['port'])}/`
  }, [endpoint])

  const handleInstall = useCallback(() => {
    if (status !== 'not-installed') return
    if (name === 'ipython' || name === 'tensorboard' || name === 'theia') {
      post({ endpoints: [name] }).then(() => {
        if (response.ok) {
          enqueueSnackbar(`Installing ${title}`, { variant: 'success' })
        } else {
          return response.text().then(text => Promise.reject(Error(text)))
        }
      }).catch((error) => {
        const message = error != null && error.message != null
          ? `Failed to enable ${title}: ${String(error.message)}`
          : `Failed to enable ${title}`
        enqueueSnackbar(message, { variant: 'error' })
      })
    }
  }, [name, response, post, enqueueSnackbar, title, status])

  const prevStatus = usePreviousDistinct(status)
  useEffect(() => {
    if (status === 'installed' && prevStatus !== undefined) {
      enqueueSnackbar(`${title} is successfully installed.`, {
        variant: 'info',
        action: (
          <Button
            href={href as string}
            target="_blank"
            rel="noopener noreferrer"
            color="inherit"
          >
            Open
          </Button>
        )
      })
    }
  }, [enqueueSnackbar, href, prevStatus, status, title])

  const cardMediaStyles = useCardMediaStyles()
  const backdropStyles = useBackdropStyles()

  return (
    <Grid item>
      <Card variant="outlined">
        <CardActionArea
          component={href !== undefined ? 'a' : 'button'}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          disabled={status === 'installing'}
          onClick={handleInstall}
        >
          <CardMedia
            image={icon}
            title={title}
            classes={cardMediaStyles}
          />
          <Backdrop open invisible={status === 'installed'} classes={backdropStyles}>
            { status === 'installing' ? <CircularProgress color="inherit"/> : null }
          </Backdrop>
        </CardActionArea>
      </Card>
      <Typography variant="caption" align="center" component="div">{title}</Typography>
    </Grid>
  )
}

export default App
