import React, {
  FunctionComponent,
  useCallback,
  useState,
  useMemo
} from 'react';
import MaterialTable, { Options, MaterialTableProps } from 'material-table';

import { Job } from '../utils';

interface JobsTableProps extends Omit<
  MaterialTableProps<Job>,
  'options' | 'onChangeRowsPerPage' | 'onChangePage' | 'onRowClick'
> {
  defaultPageSize?: number;
  onLastPage?(pageSize: number): void;
}

const JobsTable: FunctionComponent<JobsTableProps> = ({
  data,
  defaultPageSize=10,
  onLastPage,
  ...props
}) => {
  const [pageSize, setPageSize] = useState(defaultPageSize);

  const handleChangeRowsPerPage = useCallback((pageSize: number) => {
    setPageSize(pageSize);
  }, [setPageSize]);
  const handleChangePage = useCallback((page: number) => {
    const maxPage = Math.ceil(data.length / pageSize) - 1;
    if (page >= maxPage && onLastPage !== undefined) {
      onLastPage(pageSize);
    }
  }, [data, pageSize, onLastPage]);

  const options = useMemo<Options>(() => ({
    padding: 'dense',
    actionsColumnIndex: -1,
    pageSize,
    sorting: false
  }), [pageSize]);

  return (
    <MaterialTable
      data={data}
      options={options}
      onChangeRowsPerPage={handleChangeRowsPerPage}
      onChangePage={handleChangePage}
      {...props}
    />
  );
};

export default JobsTable;
