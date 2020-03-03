import { useReducer, useEffect } from 'react';

const useTableData = <T extends any>(data: T[]) => {
  const [tableData, setTableData] = useReducer((currentData: T[], newData: T[]) => {
    if (currentData == null || newData == null) return newData;

    return newData.map((row, index) => {
      if (currentData.length > index) {
        row['tableData'] = currentData[index]['tableData'];
      }
      return row;
    });
  }, data);

  useEffect(() => setTableData(data), [data]);

  return tableData;
}

export default useTableData;
