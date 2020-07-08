import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useRef
} from 'react'

import { Container, Grid } from '@material-ui/core'

import { Helmet } from 'react-helmet'
import { useSnackbar } from 'notistack'

import useFetch from 'use-http-1'

import KeyList from './KeyList'
import KeyAddForm, { KeyAddFormData } from './KeyAddForm'

const Keys: FunctionComponent = () => {
  const { enqueueSnackbar } = useSnackbar()
  const keyList = useRef<KeyList | null>(null)
  const { response, post, delete: del } = useFetch('/api/keys')

  const handleDelete = useCallback((id: number) => {
    del(`/${id}`).then(() => {
      if (response.ok) {
        enqueueSnackbar('Deleted key successfully', {
          variant: 'success',
          persist: false
        })
        if (keyList.current) {
          keyList.current.get()
        }
      } else {
        throw Error(response.data)
      }
    }).catch((error) => {
      enqueueSnackbar(`Failed to delete key: ${error.message}`,
        { variant: 'error' })
    })
  }, [del, enqueueSnackbar, response])

  const handleAdd = useCallback((data: KeyAddFormData) => {
    return post(data).then(() => {
      if (response.ok) {
        enqueueSnackbar('Deleted key successfully', {
          variant: 'success',
          persist: false
        })
        if (keyList.current) {
          keyList.current.get()
        }
      } else {
        throw Error(response.data)
      }
    }).catch((error) => {
      enqueueSnackbar(`Failed to delete key: ${error.message}`,
        { variant: 'error' })
    })
  }, [post, enqueueSnackbar, response])

  return (
    <Container fixed maxWidth="lg">
      <Helmet title="My SSH Keys"/>
      <Grid container spacing={1}>
        <Grid item lg={6} xs={12}>
          <KeyList ref={keyList} onDelete={handleDelete}/>
        </Grid>
        <Grid item lg={6} xs={12}>
          <KeyAddForm onAdd={handleAdd}/>
        </Grid>
      </Grid>
    </Container>
  )
}

export default Keys
