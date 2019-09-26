import {useMediaQuery, useTheme} from "@material-ui/core";

const useCheckIsDesktop = () => {
  const theme = useTheme();
  return useMediaQuery(theme.breakpoints.up("md"));
}

export default useCheckIsDesktop
