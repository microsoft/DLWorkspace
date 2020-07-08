import * as React from 'react'
import { useContext, useEffect, useState, useCallback, useRef } from 'react'

import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  FormGroup,
  Switch,
  FormControlLabel,
  InputAdornment,
  IconButton,
  TextField, Tooltip, Link,
} from '@material-ui/core'
import { Add, FileCopy } from '@material-ui/icons'

import useFetch from 'use-http'

import Context from './Context'
import copy from 'clipboard-copy'
import { checkFinishedJob } from '../../../utlities/interactionUtlties'

interface ListProps {
  endpoints: any[];
  setOpen: any;
}

const List: React.FC<ListProps> = ({ endpoints, setOpen }) => {
  const { cluster, job } = useContext(Context)
  const handleCopy = (e: any, copyText: string) => {
    if (copyText) {
      copy(copyText).then(() => {
        setOpen(true)
      })
    }
  }
  const sortSSH = (a: any, b: any) => {
    var worker1 = a.podName.split('-').pop().replace('worker', '')
    var worker2 = b.podName.split('-').pop().replace('worker', '')
    return parseInt(worker1) - parseInt(worker2)
  }
  const finalEnpoints = endpoints.filter((endpoint: any) => endpoint['status'] === 'running').sort(
    (endpointA, endpointB) => endpointA['port'] - endpointB['port'])
  const renderIpython = (sortedEnpoints: any) => {
    const filteredIptyhon = sortedEnpoints.filter((endPoint: any) => endPoint['name'] === 'ipython')
    return filteredIptyhon.map((endpoint: any) => {
      const url = `http://${endpoint['nodeName']}.${endpoint['domain']}:${endpoint['port']}`
      return (
        <Typography key={endpoint['id']}>
          {'iPython: '}
          <Link href={url} target="_blank">{url}</Link>
        </Typography>
      )
    })
  }
  const renderTensorboard = (sortedEnpoints: any) => {
    const filteredTensorboard = sortedEnpoints.filter((endPoint: any) => endPoint['name'] === 'tensorboard')
    return filteredTensorboard.map((endpoint: any) => {
      const url = `http://${endpoint['nodeName']}.${endpoint['domain']}:${endpoint['port']}`
      return (
        <Typography key={endpoint['id']}>
          {'TensorBoard: '}
          <Link href={url} target="_blank">{url}</Link>
        </Typography>
      )
    })
  }
  const renderSSH = (sortedEnpoints: any) => {
    const filteredSSH = sortedEnpoints.filter((endPoint: any) => endPoint['name'] === 'ssh' && endPoint['id'].indexOf('ps') === -1)
    const sortedFilteredSSH = filteredSSH.sort((a: any, b: any) => sortSSH(a, b))
    return sortedFilteredSSH.map((endpoint: any) => {
      const identify = `${cluster['workStorage'].replace(/^file:\/\//i, '//')}/${job['jobParams']['workPath']}/.ssh/id_rsa`
      const host = `${endpoint['nodeName']}.${endpoint['domain']}`
      const task = job['jobParams']['jobtrainingtype'] === 'PSDistJob' ? endpoint['podName'].split('-').pop() : ''
      const command = `ssh -i ${identify} -p ${endpoint['port']} ${endpoint['username']}@${host}`
      return (
        <Typography key={endpoint['id']}>
          {task} SSH :
          <Tooltip title="Copy">
            <IconButton color="secondary" size="medium" onClick={(event) => handleCopy(event, command)} aria-label="delete">
              <FileCopy/>
            </IconButton>
          </Tooltip>
          {command}
        </Typography>
      )
    })
  }
  const renderRemain = (sortedEnpoints: any) => {
    const filterRemain = sortedEnpoints.filter((endPoint: any) => {
      return (endPoint['name'] !== 'ssh' &&
                endPoint['name'] !== 'tensorboard' &&
                endPoint['name'] !== 'ipython' &&
                 endPoint['id'].indexOf('ps') === -1)
    })
    return filterRemain.map((endpoint: any) => {
      return (
        <Typography key={endpoint['id']}>
          {`Port ${endpoint['podPort']}:`}
          <Link href={`http://${endpoint['nodeName']}.${endpoint['domain']}:${endpoint['port']}`} target="_blank">{`http://${endpoint['nodeName']}.${endpoint['domain']}:${endpoint['port']}`}</Link>
        </Typography>
      )
    })
  }

  return (
    <>
      <CardContent>
        {
          renderSSH(finalEnpoints)
        }
        {
          renderIpython(finalEnpoints)
        }
        {
          renderTensorboard(finalEnpoints)
        }
        {
          renderRemain(finalEnpoints)
        }
      </CardContent>
    </>
  )
}

interface ControllerProps {
  endpoints: any[];
  post(data: any): Promise<any>;
  status: string;
}

const Controller: React.FC<ControllerProps> = ({ endpoints, post, status }) => {
  const [sshEnabled, setSshEnabled] = useState(false)
  const [ipythonEnabled, setIpythonEnabled] = useState(false)
  const [tensorboardEnabled, setTensorboardEnabled] = useState(false)
  const [interactivePort, setInteractivePort] = useState<number>()

  const onSshChange = useCallback((event: unknown, checked: boolean) => {
    if (checked) {
      post({ endpoints: ['ssh'] })
      setSshEnabled(true)
    }
  }, [post])
  const onIpythonChange = useCallback((event: unknown, checked: boolean) => {
    if (checked) {
      post({ endpoints: ['ipython'] })
      setIpythonEnabled(true)
    }
  }, [post])
  const onTensorboardChange = useCallback((event: unknown, checked: boolean) => {
    if (checked) {
      post({ endpoints: ['tensorboard'] })
      setTensorboardEnabled(true)
    }
  }, [post])
  const onInteractivePortChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setInteractivePort(event.target.valueAsNumber)
  }, [])
  const submitInteractivePort = useCallback(() => {
    post({ endpoints: [{
      name: `port-${interactivePort}`,
      podPort: interactivePort
    }] })
  }, [post, interactivePort])

  useEffect(() => {
    console.log(status)
    if (Array.isArray(endpoints)) {
      endpoints.forEach(({ name }) => {
        if (name === 'ssh') setSshEnabled(true)
        if (name === 'ipython') setIpythonEnabled(true)
        if (name === 'tensorboard') setTensorboardEnabled(true)
      })
    }
  }, [endpoints])

  return (
    <CardContent>
      <FormGroup row>
        <FormControlLabel
          control={<Switch checked={sshEnabled} disabled={sshEnabled || checkFinishedJob(status)} onChange={onSshChange}/>}
          label="SSH"
        />
        <FormControlLabel
          control={<Switch checked={ipythonEnabled} disabled={ipythonEnabled || checkFinishedJob(status)} onChange={onIpythonChange}/>}
          label="iPython"
        />
        <FormControlLabel
          control={<Switch checked={tensorboardEnabled} disabled={tensorboardEnabled || checkFinishedJob(status)} onChange={onTensorboardChange}/>}
          label="Tensorboard (will listen on directory ~/tensorboard/<DLWS_JOB_ID>/logs inside docker container.)"
        />
      </FormGroup>
      <TextField
        type="number"
        required
        fullWidth
        variant="outlined"
        error={interactivePort !== undefined && (interactivePort < 40000 || interactivePort > 49999) }
        label="New Interactive Port (40000-49999)"
        value={interactivePort}
        onSubmit={submitInteractivePort}
        onChange={onInteractivePortChange}
        disabled={checkFinishedJob(status)}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton edge="end" onClick={submitInteractivePort}>
                <Add/>
              </IconButton>
            </InputAdornment>
          ),
        }}
      />
    </CardContent>
  )
}
interface EndpointsProps {
  setOpen: any;
  status: string;
}
const Endpoints: React.FC<EndpointsProps> = ({ setOpen, status }) => {
  const { clusterId, jobId } = useContext(Context)
  const { data, get, post } = useFetch(`/api/clusters/${clusterId}/jobs/${jobId}/endpoints`, { onMount: true })

  const refreshTimeout = useRef<number | null>(null)
  const refreshFunction: TimerHandler = useCallback(async () => {
    refreshTimeout.current = null
    await get()
    refreshTimeout.current = setTimeout(refreshFunction, 5000)
  }, [])

  useEffect(() => {
    refreshFunction()
    return () => {
      if (refreshTimeout.current != null) {
        clearTimeout(refreshTimeout.current)
      }
    }
  }, [refreshFunction])

  return (
    <>
      <Card>
        <CardHeader
          title="Mapped Endpoints"
          subheader="Links to access interactive/visualization interface"
        />
        { Array.isArray(data) && data.length > 0 && <List endpoints={data} setOpen={setOpen}/> }
        <Controller endpoints={data} post={post} status={status} />
      </Card>
    </>
  )
}

export default Endpoints
