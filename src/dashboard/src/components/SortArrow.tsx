import React from 'react';
import { ArrowUpward } from '@material-ui/icons';

const SortArrow = React.forwardRef<SVGSVGElement>((props, ref) => (
  <ArrowUpward {...props} fontSize="small" ref={ref}/>
));

export default SortArrow;
