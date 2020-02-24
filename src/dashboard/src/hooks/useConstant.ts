import { useMemo } from 'react';

// eslint-disable-next-line react-hooks/exhaustive-deps
const useConstant = <T>(value: T) => useMemo(() => value, []);

export default useConstant
