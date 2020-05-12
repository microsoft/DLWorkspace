import React, {
  FunctionComponent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import { Options, MaterialTableProps } from 'material-table';
import { zipWith } from 'lodash';

import SvgIconsMaterialTable from '../../../components/SvgIconsMaterialTable';

import { Job } from '../utils';

import DetailPanel from './DetailPanel';

interface JobsTableProps extends Omit<
  MaterialTableProps<Job>,
  'data' | 'options' | 'onChangeRowsPerPage' | 'onChangePage' | 'onRowClick'
> {
  jobs: Array<Job>;
  defaultPageSize?: number;
  selection?: boolean;
  onLastPage?(pageSize: number): void;
}

const JobsTable: FunctionComponent<JobsTableProps> = ({
  jobs,
  defaultPageSize=10,
  selection=false,
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

  const options = useRef<Options>({
    padding: 'dense',
    actionsColumnIndex: -1,
    sorting: true,
    draggable: false,
    pageSize: defaultPageSize,
    selection
  }).current;

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
    <SvgIconsMaterialTable
      data={data}
      options={options}
      detailPanel={detailPanel}
      localization={{
        body: {
          emptyDataSourceMessage: 'No jobs to display'
        },
        pagination: {
          labelRowsSelect: 'jobs',
          labelRowsPerPage: 'Jobs per page',
        },
        toolbar: {
          nRowsSelected: '{0} job(s) selected:'
        }
      }}
      onChangeRowsPerPage={handleChangeRowsPerPage}
      onChangePage={handleChangePage}
      {...props}
    />
  );
};

export default JobsTable;
