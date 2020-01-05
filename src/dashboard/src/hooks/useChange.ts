import {
  useEffect,
  useRef
} from 'react';

const useChange = <T>(callback: (value: T, prevValue: T) => void, value: T) => {
  const ref = useRef<T>(value);
  useEffect(() => {
    if (value !== ref.current) {
      const prevValue = ref.current;
      ref.current = value;
      callback(value, prevValue);
    }
  }, [callback, value]);
}

export default useChange;
