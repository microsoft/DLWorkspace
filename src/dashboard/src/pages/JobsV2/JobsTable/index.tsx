import React, {
  FunctionComponent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import MaterialTable, { Options, MaterialTableProps } from 'material-table';
import { zipWith } from 'lodash';

import { Job } from '../utils';

import DetailPanel from './DetailPanel';

interface JobsTableProps extends Omit<
  MaterialTableProps<Job>,
  'data' | 'options' | 'onChangeRowsPerPage' | 'onChangePage' | 'onRowClick'
> {
  jobs: Array<Job>;
  defaultPageSize?: number;
  onLastPage?(pageSize: number): void;
}

const JobsTable: FunctionComponent<JobsTableProps> = ({
  jobs,
  defaultPageSize=10,
  onLastPage,
  ...props
}) => {
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const [data, setData] = useState(jobs);

  const detailPanel = useCallback((job: Job) => {
    return <DetailPanel job={job}/>;
  }, []);
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
    sorting: false,
    pageSize: defaultPageSize
  }), [defaultPageSize]);

  useEffect(() => {
    setData((data) => {
      if (data === undefined) return jobs;
      if (jobs === undefined) return data;
      return zipWith(data, jobs, (currentJob, newJob) => {
        if (currentJob === undefined) return newJob;
        if (newJob === undefined) return undefined;
        newJob.tableData = currentJob.tableData
        return newJob
      }).filter(Boolean)
    })
  }, [jobs])

  return (
    <MaterialTable
      data={data}
      options={options}
      detailPanel={detailPanel}
      onChangeRowsPerPage={handleChangeRowsPerPage}
      onChangePage={handleChangePage}
      {...props}
    />
  );
};

export default JobsTable;
