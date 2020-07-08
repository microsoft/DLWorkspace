import { useRef } from 'react'

const useConstant = <T>(value: T) => useRef(value).current

export default useConstant
