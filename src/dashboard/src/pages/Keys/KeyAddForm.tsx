import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useEffect,
  useState
} from 'react'

import {
  Button,
  Card,
  CardHeader,
  CardContent,
  CardActions,
  CircularProgress,
  TextField
} from '@material-ui/core'

import { useForm, Controller } from 'react-hook-form'

export interface KeyAddFormData {
  name: string
  key: string
}

interface KeyAddFormProps {
  onAdd(data: KeyAddFormData): Promise<void>
}

const KeyAddForm: FunctionComponent<KeyAddFormProps> = ({ onAdd }) => {
  const {
    handleSubmit,
    reset,
    getValues,
    setValue,
    watch,
    control,
    errors
  } = useForm<KeyAddFormData>({
    defaultValues: {
      name: '',
      key: ''
    }
  })
  const [busy, setBusy] = useState(false)
  const key = watch('key')

  useEffect(() => {
    const name = getValues('name')
    if (name !== '') return

    const keyParts = key.split(' ', 3)
    if (keyParts.length < 3) return
    const inferredName = keyParts[2]
    if (inferredName.indexOf('@') === -1) return

    setValue('name', inferredName)
  }, [key, getValues, setValue])

  const handleFormSubmit = useCallback((keyItem) => {
    if (busy) return
    setBusy(true)
    onAdd(keyItem).then(() => {
      reset()
      setBusy(false)
    }, () => {
      setBusy(false)
    })
  }, [busy, setBusy, onAdd, reset])

  return (
    <Card component="form" onSubmit={handleSubmit(handleFormSubmit)}>
      <CardHeader
        title="Add New"
        subheader="will be enabled in newly submitted jobs"
      />
      <CardContent>
        <Controller
          as={TextField}
          control={control}
          rules={{ required: true }}
          variant="outlined"
          margin="dense"
          size="small"
          fullWidth
          label="Name"
          placeholder="user@hostname"
          required
          name="name"
          error={errors.name !== undefined}
          helperText={errors.name && errors.name.message}
        />
        <Controller
          as={TextField}
          control={control}
          rules={{ required: true }}
          variant="outlined"
          margin="dense"
          size="small"
          fullWidth
          multiline
          rows={5}
          label="Key"
          placeholder="Paste your public key here..."
          required
          name="key"
          error={errors.key !== undefined}
          helperText={errors.key && errors.key.message}
        />
      </CardContent>
      <CardActions>
        <Button type="submit" color="primary" disabled={busy}>
          { busy ? <CircularProgress size="1em"/> : 'Add' }
        </Button>
      </CardActions>
    </Card>
  )
}

export default KeyAddForm
