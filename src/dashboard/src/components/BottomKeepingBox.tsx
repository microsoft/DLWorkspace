import * as React from 'react'
import {
  FunctionComponent,
  useEffect,
  useRef,
} from 'react'

import {
  Box,
  BoxProps
} from '@material-ui/core'

const BottomKeepingBox: FunctionComponent<BoxProps> = (props) => {
  const box = useRef<HTMLElement>()
  const scrollBottom = useRef(0)

  useEffect(() => {
    if (box.current !== undefined) {
      if (scrollBottom.current === 0) {
        const { scrollHeight, clientHeight } = box.current
        box.current.scrollTop = scrollHeight - clientHeight
      }
    }
  })

  if (box.current !== undefined) {
    const { scrollHeight, scrollTop, clientHeight } = box.current
    scrollBottom.current = scrollHeight - scrollTop - clientHeight
  }

  return (
    <Box
      overflow="auto"
      {...props}
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore: https://github.com/mui-org/material-ui/issues/17010
      ref={box}
    />
  )
}

export default BottomKeepingBox
