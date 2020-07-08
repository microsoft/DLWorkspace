import * as React from 'react'
import {
  FunctionComponent,
  RefObject,
  createRef,
  forwardRef,
  useCallback,
  useContext,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
} from 'react'

import {
  Button,
  Card,
  CardHeader,
  CardContent,
  CardActions,
  CircularProgress,
  Container,
  Grid,
  List,
  ListItem,
  ListItemSecondaryAction,
  ListItemText,
  TextField,
  Tooltip,
  colors,
} from '@material-ui/core'
import {
  Close,
  Error,
  Warning,
} from '@material-ui/icons'

import { useForm, Controller } from 'react-hook-form'
import useFetch from 'use-http-1'

import ClustersContext from '../../contexts/Clusters'

interface ClusterListItem {
  update(data: UpdateFormData): void;
}

interface ClusterListItemProps {
  id: string;
}

const ClusterListItem = forwardRef<ClusterListItem, ClusterListItemProps>(({ id }, ref) => {
  const { data: config } = useFetch(`/api/clusters/${id}`, [id])
  const { data, loading, error, get, put } = useFetch(`/api/clusters/${id}/allowed-ip`)

  const supportAllowedIp = useMemo(() => {
    if (config === undefined) return undefined
    return Boolean(config.supportAllowedIp)
  }, [config])
  const ip = useMemo(() => {
    if (data == null) return undefined
    if (data.ip == null) return undefined
    return String(data.ip)
  }, [data])
  const expired = useMemo(() => {
    if (data == null) return undefined
    if (data['valid_until'] == null) return undefined
    return new Date(Date.parse(data['valid_until']))
  }, [data])

  useEffect(() => {
    if (supportAllowedIp) {
      get()
    }
  }, [supportAllowedIp, get])

  useImperativeHandle(ref, () => ({
    update(data) {
      if (supportAllowedIp !== true) return
      put(data).then(() => get(), (error) => {
        console.error(error)
      })
    }
  }), [supportAllowedIp, put, get])

  const secondary = useMemo(() => {
    if (ip && expired) {
      return `${ip} until ${expired.toLocaleString()}`
    }
    if (error && error.name === '404') {
      return 'Not configured'
    }
  }, [ip, expired, error])

  const icon = useMemo(() => {
    if (supportAllowedIp === undefined || loading) {
      return <CircularProgress size={24}/>
    }
    if (!supportAllowedIp) {
      return (
        <Tooltip title="Corp only/Not available in this cluster">
          <Close color="error"/>
        </Tooltip>
      )
    }
    if (error && error.name !== '404') {
      return (
        <Tooltip title={`Failed to fetch the record: ${error.message}`}>
          <Error color="error"/>
        </Tooltip>
      )
    }
    if (expired && expired.valueOf() - Date.now() <= 7 * 24 * 60 * 60 * 1000) {
      return (
        <Tooltip title="Expire soon">
          <Warning htmlColor={colors.yellow[800]}/>
        </Tooltip>
      )
    }
    return null
  }, [supportAllowedIp, loading, error, expired])

  return (
    <ListItem>
      <ListItemText
        primary={id}
        secondary={secondary}
      />
      { icon !== null && (
        <ListItemSecondaryAction children={icon}/>
      ) }
    </ListItem>
  )
})

interface UpdateFormData {
  ip: string;
}

interface UpdateFormProps {
  onSubmit(data: UpdateFormData): void;
}

const IPV4_PATTERN = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/

const UpdateForm: FunctionComponent<UpdateFormProps> = ({ onSubmit }) => {
  const {
    handleSubmit,
    reset,
    control,
    errors
  } = useForm<UpdateFormData>({ defaultValues: { ip: '' } })

  const { data } = useFetch('https://httpbin.org/ip', [])

  const handleResetClick = useCallback(() => reset(), [reset])

  useEffect(() => {
    if (typeof data === 'object' && typeof data.origin === 'string') {
      reset({ ip: data.origin })
    }
  }, [data, reset])

  return (
    <Card component="form" onSubmit={handleSubmit(onSubmit)}>
      <CardHeader
        title="Update Allowed IP"
        subheader="It takes several minutes to take effect for Azure clusters. Non-Azure clusters do not have IP allow list."
      />
      <CardContent>
        <Controller
          as={TextField}
          control={control}
          rules={{ required: true, pattern: IPV4_PATTERN }}
          variant="outlined"
          margin="dense"
          size="small"
          fullWidth
          label="IP Address"
          required
          name="ip"
          error={errors.ip !== undefined}
          helperText={errors.ip && errors.ip.message}
        />
      </CardContent>
      <CardActions>
        <Button onClick={handleResetClick}>Reset</Button>
        <Button type="submit" color="primary">Update</Button>
      </CardActions>
    </Card>
  )
}

const AllowedIP: FunctionComponent = () => {
  const { clusters } = useContext(ClustersContext)
  const itemsRef = useRef<Map<string, RefObject<ClusterListItem>>>(new Map())
  const handleUpdateFormSubmit = useCallback((data) => {
    for (const { id } of clusters) {
      const itemRef = itemsRef.current.get(id)
      if (itemRef && itemRef.current) {
        itemRef.current.update(data)
      }
    }
  }, [clusters])

  useEffect(() => {
    for (const itemId of Object.keys(itemsRef.current)) {
      if (clusters.every(({ id }) => id !== itemId)) {
        itemsRef.current.delete(itemId)
      }
    }
  }, [clusters])

  return (
    <Container maxWidth="lg">
      <Grid container spacing={3}>
        <Grid item xs={12} lg={6}>
          <Card>
            <CardHeader title="Allowed IP in Clusters"/>
            <List disablePadding dense>
              {
                clusters.map(({ id }) => {
                  if (!itemsRef.current.has(id)) {
                    itemsRef.current.set(id, createRef())
                  }
                  return (
                    <ClusterListItem
                      key={id}
                      ref={itemsRef.current.get(id)}
                      id={id}
                    />
                  )
                })
              }
            </List>
          </Card>
        </Grid>
        <Grid item xs={12} lg={6}>
          <UpdateForm onSubmit={handleUpdateFormSubmit}/>
        </Grid>
      </Grid>
    </Container>
  )
}

export default AllowedIP
