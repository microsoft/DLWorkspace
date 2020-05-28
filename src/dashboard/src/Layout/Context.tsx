import {
  Dispatch,
  FunctionComponent,
  SetStateAction,
  createContext,
  createElement,
  useState
} from 'react';

interface LayoutContext {
  drawerOpen: boolean;
  setDrawerOpen: Dispatch<SetStateAction<boolean>>;
}

const LayoutContext = createContext<LayoutContext>({
  drawerOpen: false,
  setDrawerOpen () { return; }
});

const LayoutProvider: FunctionComponent = ({ children }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const value = { drawerOpen, setDrawerOpen };

  return createElement(LayoutContext.Provider, { value }, children);
};

export default LayoutContext;
export { LayoutProvider };
