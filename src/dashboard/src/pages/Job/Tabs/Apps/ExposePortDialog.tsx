import * as React from 'react'
import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useState
} from 'react'

import { useForm } from 'react-hook-form'

import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField
} from '@material-ui/core'

interface ExposePortFormData {
  port: string
}

interface ExposePortDialog {
  open: () => void
}

interface ExposePortDialogProps {
  onExpose: (port: number) => void
}

const ExposePortDialog = forwardRef<ExposePortDialog, ExposePortDialogProps>(({ onExpose }, ref) => {
  const [open, setOpen] = useState(false)
  const {
    handleSubmit,
    register,
    errors
  } = useForm<ExposePortFormData>()

  const handleClose = useCallback(() => {
    setOpen(false)
  }, [setOpen])
  const handleExpose = handleSubmit(({ port }) => {
    onExpose(Number(port))
    setOpen(false)
  })

  useImperativeHandle(ref, () => ({
    open () {
      setOpen(true)
    }
  }), [setOpen])

  return (
    <Dialog open={open} onClose={handleClose}>
      <form onSubmit={handleExpose}>
        <DialogTitle>Expose a Port</DialogTitle>
        <DialogContent>
          <TextField
            type="number"
            variant="outlined"
            margin="dense"
            size="small"
            fullWidth
            label="Port"
            required
            name="port"
            error={errors.port !== undefined}
            helperText={'40000 - 49999'}
            inputRef={register({
              required: true,
              min: 40000,
              max: 49999
            })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Close</Button>
          <Button type="submit" color="primary">Expose</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
})

export default ExposePortDialog
