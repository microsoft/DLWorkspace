import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  useLocation,
  useHistory,
} from 'react-router';

const useHashTab = (...hashes: readonly string[]) => {
  const hashesRef = useRef(hashes).current;

  const { hash } = useLocation();
  const { replace } = useHistory();
  const cleanHash = useMemo(() => hash[0] === '#' ? hash.slice(1) : hash, [hash]);
  const [index, setIndex] = useState<number>(
    () => Math.max(hashesRef.indexOf(cleanHash), 0))

  useEffect(() => {
    const hashIndex = hashesRef.indexOf(cleanHash);
    if (hashIndex !== -1) {
      setIndex(hashIndex);
    }
  }, [hashesRef, cleanHash]);
  useEffect(() => {
    replace({ hash: hashesRef[index] });
  }, [replace, hashesRef, index]);

  return [index, setIndex] as const;
};

export default useHashTab;
