import * as React from 'react'
import {
  FunctionComponent,
  FormEvent,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  useMemo
} from 'react'
import {
  Box,
  FormGroup,
  FormControlLabel,
  IconButton,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  Switch,
  TextField,
  Typography
} from '@material-ui/core'
import {
  Send
} from '@material-ui/icons'
import useFetch from 'use-http-1'
import { useSnackbar } from 'notistack'

import Loading from '../../../components/Loading'
import CopyableTextListItem from '../../../components/CopyableTextListItem'

import useRouteParams from '../useRouteParams'
import Context from '../Context'

const EndpointListItem: FunctionComponent<{ endpoint: any }> = ({ endpoint }) => {
  const { cluster, job } = useContext(Context)
  if (endpoint.status !== 'running') return null
  if (endpoint.name === 'ssh') {
    const identify = `${cluster['workStorage'].replace(/^file:\/\//i, '//')}/${job['jobParams']['workPath']}/.ssh/id_rsa`
    const host = `${endpoint['nodeName']}.${endpoint['domain']}`
    const task = job['jobParams']['jobtrainingtype'] === 'PSDistJob'
      ? endpoint['role-name'] && endpoint['role-idx']
        ? `SSH to ${endpoint['role-name']}-${endpoint['role-idx']}`
        : `SSH to ${endpoint['podName'].split('-').pop()}`
      : 'SSH'
    const command = `ssh -i ${identify} -p ${endpoint['port']} ${endpoint['username']}@${host}`
    return <CopyableTextListItem primary={task} secondary={command}/>
  }
  const url = `http://${endpoint['nodeName']}.${endpoint['domain']}:${endpoint['port']}/`
  if (endpoint.name === 'ipython') {
    return (
      <ListItem button component="a" href={url} target="_blank">
        <ListItemText primary="iPython" secondary={url}/>
      </ListItem>
    )
  }
  if (endpoint.name === 'tensorboard') {
    return (
      <ListItem button component="a" href={url} target="_blank">
        <ListItemText primary="Tensorboard" secondary={url}/>
      </ListItem>
    )
  }
  if (endpoint.name === 'theia') {
    return (
      <ListItem button component="a" href={url} target="_blank">
        <ListItemText primary="Visual Studio Code in DLTS (alpha)" secondary={url}/>
      </ListItem>
    );
  }
  return (
    <ListItem button component="a" href={url} target="_blank">
      <ListItemText primary={`Port ${endpoint['podPort']}`} secondary={url}/>
    </ListItem>
  )
}

const EndpointsList: FunctionComponent<{
  endpoints: any[]
}> = ({ endpoints }) => {
  const sortedEndpoints = useMemo(() => {
    const nameOrders = ['ssh', 'ipython', 'tensorboard', 'theia'].reverse()
    return endpoints.filter((endpoint) => {
      return endpoint.status === 'running'
    }).sort((endpointA, endpointB) => {
      const nameOrderA = nameOrders.indexOf(endpointA['name'])
      const nameOrderB = nameOrders.indexOf(endpointB['name'])
      if (nameOrderA !== nameOrderB) {
        return nameOrderB - nameOrderA
      }
      if (endpointA.name === 'ssh') {
        return String(endpointA['podName']).localeCompare(String(endpointB['podName']))
      }
      return endpointA['port'] - endpointB['port']
    })
  }, [endpoints])
  return (
    <List dense>
      {sortedEndpoints.map((endpoint) => {
        return <EndpointListItem key={endpoint.id} endpoint={endpoint}/>
      })}
    </List>
  )
}

interface EndpointSwitchProps {
  label: string
  endpoint: string
  enabled: boolean
}

const EndpointSwitch: FunctionComponent<EndpointSwitchProps> = ({ label, endpoint, enabled }) => {
  const { clusterId, jobId } = useRouteParams()
  const { enqueueSnackbar } = useSnackbar()

  const [checked, setChecked] = useState(enabled)

  const { response, post } = useFetch(
    `/api/clusters/${clusterId}/jobs/${jobId}/endpoints`,
    [clusterId, jobId])

  const handleChange = useCallback(() => {
    setChecked(true)
    post({ endpoints: [endpoint] })
      .then(() => {
        if (response.ok) {
          enqueueSnackbar(`${label} enabled`, { variant: 'success' })
        } else {
          return response.text().then(text => Promise.reject(Error(text)))
        }
      }).catch(error => {
        const message = error && error.message
          ? `Failed to enable ${label}: ${error.message}`
          : `Failed to enable ${label}`
        enqueueSnackbar(message, { variant: 'error' })
        setChecked(false)
      })
  }, [post, endpoint, response, enqueueSnackbar, label])

  useEffect(() => {
    // Only sync `checked` state when `enabled` prop changes
    setChecked(enabled)
  }, [enabled])

  return (
    <FormControlLabel
      checked={checked}
      disabled={checked}
      control={<Switch/>}
      label={label}
      onChange={handleChange}
    />
  )
}

const EndpointsController: FunctionComponent<{ endpoints: any[] }> = ({ endpoints }) => {
  const { clusterId, jobId } = useRouteParams()
  const { enqueueSnackbar } = useSnackbar()
  const ssh = useMemo(() => {
    return endpoints.some((endpoint) => endpoint.name === 'ssh')
  }, [endpoints])
  const ipython = useMemo(() => {
    return endpoints.some((endpoint) => endpoint.name === 'ipython')
  }, [endpoints])
  const tensorboard = useMemo(() => {
    return endpoints.some((endpoint) => endpoint.name === 'tensorboard')
  }, [endpoints])
  const theia = useMemo(() => {
    return endpoints.some((endpoint) => endpoint.name === 'theia')
  }, [endpoints])
  const { post } =
    useFetch(`/api/clusters/${clusterId}/jobs/${jobId}/endpoints`,
      [clusterId, jobId])
  const portInput = useRef<HTMLInputElement>()
  const onSubmit = useCallback((event: FormEvent) => {
    event.preventDefault()
    if (portInput.current === undefined) return
    const port = portInput.current.valueAsNumber
    enqueueSnackbar(`Exposing port ${port}...`)
    post({
      endpoints: [{
        name: `port-${port}`,
        podPort: port
      }]
    }).then(() => {
      enqueueSnackbar(`Port ${port} exposed`, { variant: 'success' })
    }, () => {
      enqueueSnackbar(`Failed to expose port ${port}`, { variant: 'error' })
    })
  }, [post, enqueueSnackbar])

  return (
    <Box px={2}>
      <FormGroup aria-label="position" row>
        <EndpointSwitch label="SSH" endpoint="ssh" enabled={ssh}/>
        <EndpointSwitch label="iPython" endpoint="ipython" enabled={ipython}/>
        <EndpointSwitch label="Tensorboard" endpoint="tensorboard" enabled={tensorboard}/>
        <EndpointSwitch label="Visual Studio Code in DLTS (alpha)" endpoint="theia" enabled={theia}/>
      </FormGroup>
      <Typography>
        *: Tensorboard will listen on directory
        <code> ~/tensorboard/$DLWS_JOB_ID/logs </code>
        inside docker container.
      </Typography>
      <Box pt={1} pb={2} component="form" onSubmit={onSubmit}>
        <TextField
          inputRef={portInput}
          type="number"
          fullWidth
          label="New Interactive Port"
          placeholder="40000 - 49999"
          inputProps={{ min: '40000', max: '49999' }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton type="submit">
                  <Send/>
                </IconButton>
              </InputAdornment>
            )
          }}
        />
      </Box>
    </Box>
  )
}

const Endpoints: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams()
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { job } = useContext(Context)
  const { error, data, get } =
    useFetch(`/api/clusters/${clusterId}/jobs/${jobId}/endpoints`,
      [clusterId, jobId])
  const [endpoints, setEndpoints] = useState<any[]>()

  useEffect(() => {
    if (data !== undefined) {
      setEndpoints(data)

      const timeout = setTimeout(get, 3000)
      return () => {
        clearTimeout(timeout)
      }
    }
  }, [data, get])
  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch job endpoints: ${clusterId}/${jobId}`, {
        variant: 'error',
        persist: true
      })
      return () => {
        if (key !== null) closeSnackbar(key)
      }
    }
  }, [error, enqueueSnackbar, closeSnackbar, clusterId, jobId])

  if (endpoints === undefined) {
    return <Loading/>
  }

  return (
    <>
      {job['jobStatus'] === 'running' && <EndpointsList endpoints={endpoints}/>}
      <EndpointsController endpoints={endpoints}/>
    </>
  )
}

Endpoints.displayName = 'Endpoints'

export default Endpoints
