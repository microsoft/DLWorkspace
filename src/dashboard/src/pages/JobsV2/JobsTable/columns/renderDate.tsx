import React from 'react';
import { Tooltip } from '@material-ui/core';
import { formatDistanceToNow } from 'date-fns';

const renderDate = (date: Date) => {
  if (isNaN(date.valueOf())) return null;
  return (
    <Tooltip title={date.toLocaleString()}>
      <span style={{ whiteSpace: "nowrap" }}>
        {formatDistanceToNow(date, { includeSeconds: true, addSuffix: true })}
      </span>
    </Tooltip>
  );
}

export default renderDate;
