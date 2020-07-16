import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useContext,
  useState
} from 'react'

import useFetch from 'use-http-1'
import { useForm } from 'react-hook-form'

import {
  Box,
  CircularProgress,
  Divider,
  IconButton,
  Link,
  List,
  ListItem,
  ListItemText,
  OutlinedInput,
  createStyles,
  makeStyles
} from '@material-ui/core'
import {
  AccountBox,
  Check,
  Close,
  Group,
  Remove
} from '@material-ui/icons'

import { useSnackbar } from 'notistack'

import { get } from 'lodash'

import CodeBlock from '../../../components/CodeBlock'
import CopyableTextListItem from '../../../components/CopyableTextListItem'

import useRouteParams from '../useRouteParams'
import Context from '../Context'

const useInputStyles = makeStyles(() => createStyles({
  input: {
    width: '3em'
  }
}))

const InferenceGPUsListItem: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams()
  const { enqueueSnackbar } = useSnackbar()
  const { job } = useContext(Context)

  const { response, post, abort } = useFetch(`/api/clusters/${clusterId}/jobs/${jobId}/gpus`)

  const { register, errors, handleSubmit } = useForm({
    defaultValues: {
      min: String(job['jobParams']['mingpu']),
      max: String(job['jobParams']['maxgpu'])
    }
  })

  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)

  const handleGpusSubmit = handleSubmit(({ min, max }) => {
    setBusy(true)
    post({ min: Number(min), max: Number(max) }).then(() => {
      if (!response.ok) {
        return response.text().then(text => Promise.reject(Error(text)))
      }
      setBusy(false)
      setEditing(false)
      enqueueSnackbar('Scaled job successfully', { variant: 'success' })
    }).catch((error) => {
      if (error != null && typeof error.message === 'string') {
        enqueueSnackbar(`Failed to scale job: ${error.message}`, { variant: 'error' })
      } else {
        enqueueSnackbar('Failed to scale job', { variant: 'error' })
      }
      setBusy(false)
    })
  })

  const handleEditClick = useCallback(() => {
    setBusy(false)
    setEditing(true)
  }, [setEditing])
  const handleCancelClick = useCallback(() => {
    abort()
    setBusy(false)
    setEditing(false)
  }, [abort, setEditing])

  const inputStyles = useInputStyles()

  if (editing) {
    return (
      <ListItem>
        <ListItemText
          primary="GPUs to Use"
          secondaryTypographyProps={{ component: 'form', onSubmit: handleGpusSubmit }}
          secondary={(
            <>
              {'Min: '}
              <OutlinedInput
                type="number"
                name="min"
                disabled={busy}
                margin="dense"
                classes={inputStyles}
                error={errors.min !== undefined}
                inputRef={register({ required: true, min: 0 })}
              />
              {' Max: '}
              <OutlinedInput
                type="number"
                name="max"
                disabled={busy}
                margin="dense"
                classes={inputStyles}
                error={errors.max !== undefined}
                inputRef={register({ required: true, min: 0 })}
              />
              {' '}
              <IconButton type="submit" disabled={busy}>
                { !busy && <Check/> }
                { busy && <CircularProgress size={24}/> }
              </IconButton>
              {' '}
              <IconButton onClick={handleCancelClick}><Close/></IconButton>
            </>
          )}
        />
      </ListItem>
    )
  } else {
    return (
      <ListItem>
        <ListItemText
          primary="GPUs to Use"
          secondary={(
            <>
              {`Min: ${job['jobParams']['mingpu']} Max: ${job['jobParams']['maxgpu']} `}
              <Link component="button" onClick={handleEditClick}>edit</Link>
            </>
          )}
        />
      </ListItem>
    )
  }
}

const Brief: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams()
  const { cluster, job } = useContext(Context)

  const submitted = new Date(get(job, 'jobTime'))
  const started = new Date(get(job, 'jobStatusDetail.0.startedAt'))
  const finished = new Date(get(job, 'jobStatusDetail.0.finishedAt'))
  return (
    <List dense disablePadding>
      <CopyableTextListItem primary="Job Id" secondary={jobId}/>
      <ListItem>
        <ListItemText
          primary="Job Owner"
          secondary={(
            <Box display="flex" alignItems="center">
              <Group/>
              <Box paddingLeft={1} paddingRight={2}>{job['vcName']}</Box>
              <AccountBox/>
              <Box paddingLeft={1}>{job['userName']}</Box>
            </Box>
          )}
          secondaryTypographyProps={{ component: 'div' }}
        />
      </ListItem>
      { isFinite(submitted.valueOf()) && (
        <ListItem>
          <ListItemText primary="Job Submitted Time" secondary={submitted.toLocaleString()}/>
        </ListItem>
      ) }
      { isFinite(started.valueOf()) && (
        <ListItem>
          <ListItemText primary="Job Started Time" secondary={started.toLocaleString()}/>
        </ListItem>
      ) }
      { isFinite(finished.valueOf()) && (
        <ListItem>
          <ListItemText primary="Job Finished Time" secondary={finished.toLocaleString()}/>
        </ListItem>
      ) }
      <Divider />
      <ListItem>
        <ListItemText primary="Job Type" secondary={get(job, 'jobParams.jobtrainingtype')}/>
      </ListItem>
      <ListItem>
        <ListItemText
          primary="Cluster"
          secondary={clusterId}
        />
      </ListItem>
      {
        job['jobParams']['jobtrainingtype'] === 'PSDistJob' && (
          <ListItem>
            <ListItemText
              primary="Number of Nodes"
              secondary={job['jobParams']['numpsworker']}
            />
          </ListItem>
        )
      }
      {
        job['jobParams']['jobtrainingtype'] === 'PSDistJob' && (
          <ListItem>
            <ListItemText
              primary="Total of GPUs"
              secondary={job['jobParams']['numpsworker'] * job['jobParams']['resourcegpu']}
            />
          </ListItem>
        )
      }
      {
        (
          job['jobParams']['jobtrainingtype'] === 'RegularJob' ||
          job['jobParams']['jobtrainingtype'] === 'InferenceJob'
        ) && (
          <ListItem>
            <ListItemText
              primary="Number of GPUS"
              secondary={job['jobParams']['resourcegpu']}
            />
          </ListItem>
        )
      }
      {
        job['jobParams']['jobtrainingtype'] === 'InferenceJob' && (
          <InferenceGPUsListItem/>
        )
      }
      <ListItem>
        <ListItemText
          primary="Preemptible"
          secondary={job['jobParams']['preemptionAllowed'] ? <Check/> : <Remove/>}
        />
      </ListItem>
      <Divider />
      <CopyableTextListItem
        primary="Data Path"
        secondary={`${cluster['dataStorage'] || ''}/${job['jobParams']['dataPath']}`}
      />
      <CopyableTextListItem
        primary="Work Path"
        secondary={`${cluster['workStorage'] || ''}/${job['jobParams']['workPath']}`}
      />
      <CopyableTextListItem
        primary="Job Path"
        secondary={`${cluster['workStorage'] || ''}/${job['jobParams']['jobPath']}`}
      />
      <Divider />
      <ListItem>
        <ListItemText primary="Docker Image" secondary={job['jobParams']['image']}/>
      </ListItem>
      <ListItem>
        <ListItemText
          primary="Command"
          secondary={<CodeBlock>{job['jobParams']['cmd']}</CodeBlock>}
          secondaryTypographyProps={{ component: 'div' }}
        />
      </ListItem>
      {
        job['jobParams']['max_retry_count'] !== undefined && (
          <>
            <Divider />
            <ListItem>
              <ListItemText
                primary="Max Retry Count"
                secondary={job['jobParams']['max_retry_count']}
              />
            </ListItem>
          </>
        )
      }
    </List>
  )
}

Brief.displayName = 'Brief'

export default Brief
