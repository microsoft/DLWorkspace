import React from 'react';
import { Tooltip } from '@material-ui/core';

import { formatDateDistance } from '../../../../../utils/formats';

const renderDate = (date: Date) => {
  if (isNaN(date.valueOf())) return null;
  return (
    <Tooltip title={date.toLocaleString()}>
      <span style={{ whiteSpace: "nowrap" }}>
        {formatDateDistance(date)}
      </span>
    </Tooltip>
  );
}

export default renderDate;
