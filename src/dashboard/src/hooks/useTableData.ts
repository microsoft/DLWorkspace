import { useReducer, useEffect } from 'react';
import { extend } from 'lodash';

const useTableData = <T extends any>(data: T[], defaults?: any) => {
  const [tableData, setTableData] = useReducer((currentData: T[], newData: T[]) => {
    if (newData == null) return newData;
    if (currentData == null) currentData = [];

    return newData.map((row, index) => {
      if (index < currentData.length) {
        row['tableData'] = currentData[index]['tableData'];
      } else if (defaults) {
        row['tableData'] = extend(row['tableData'], defaults)
      }
      return row;
    });
  }, data, (data) => {
    if (data == null || defaults == null) return data;
    return data.map((row) => {
      row['tableData'] = defaults;
      return row;
    });
  });

  useEffect(() => setTableData(data), [data]);

  return tableData;
}

export default useTableData;
