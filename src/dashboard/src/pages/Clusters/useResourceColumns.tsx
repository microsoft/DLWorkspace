import * as React from 'react';
import {
  useMemo,
  useState,
} from 'react';
import {
  TableSortLabel,
  useTheme
} from '@material-ui/core';
import { More } from '@material-ui/icons';
import { Column } from 'material-table';
import { capitalize, get } from 'lodash';

import CaptionColumnTitle from '../../components/CaptionColumnTitle';
import { formatBytes, formatFloat } from '../../utils/formats';

export type ResourceType = 'cpu' | 'gpu' | 'memory';
export type ResourceKind = 'total' | 'unschedulable' | 'used' | 'preemptable' | 'available';

const useResourceColumns = (kinds: ResourceKind[]) => {
  const theme = useTheme();

  const [expandedResourceType, setExpandedResourceType] = useState<ResourceType>('gpu');

  const typeColor = useMemo(() => ({
    cpu: theme.palette.background.default,
    gpu: theme.palette.background.paper,
    memory: theme.palette.background.default,
  }), [theme]);

  const expandable = kinds.indexOf('used') > -1 && kinds.indexOf('total') > -1;

  return useMemo(() => {
    const columns: Column<any>[] = [];

    for (const title of ['CPU', 'GPU', 'Memory']) {
      const type = title.toLowerCase() as ResourceType;
      const process = type === 'memory' ? formatBytes : formatFloat;
      const style = { backgroundColor: typeColor[type] };
      columns.push({
        title: (
          <TableSortLabel
            active
            IconComponent={More}
            direction="desc"
            onClick={() => setExpandedResourceType(type)}
          >
            <CaptionColumnTitle caption="Used/Total">
              {title}
            </CaptionColumnTitle>
          </TableSortLabel>
        ),
        hidden: !expandable || expandedResourceType === type,
        headerStyle: { whiteSpace: 'nowrap', ...style },
        cellStyle: { whiteSpace: 'nowrap', ...style },
        render: ({ status }) => status && (
          <>
            {process(get(status, [type, 'used'], 0))}
            /
            {process(get(status, [type, 'total'], 0))}
          </>
        ),
        sorting: false,
        searchable: false,
        width: 'auto'
      });
      for (const kind of kinds) {
        columns.push({
          title: (
            <CaptionColumnTitle caption={capitalize(kind)}>
              {title}
            </CaptionColumnTitle>
          ),
          type: 'numeric',
          field: `status.${type}.${kind}`,
          hidden: expandable && expandedResourceType !== type,
          render: ({ status }) => status && (
            <>{process(get(status, [type, kind], 0))}</>
          ),
          headerStyle: style,
          cellStyle: style,
          width: 'auto'
        });
      }
    }
    return columns;
  }, [kinds, expandable, expandedResourceType, typeColor]);
};

export default useResourceColumns;
