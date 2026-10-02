from abc import ABC, abstractmethod
from typing_extensions import Self

import os
import polars as pl

# INPUT.PY --- 
#   Handles all tasks related to reading + cleaning data.



class INPUT_DIRECTORY(ABC):
    def __init__(self, project_directory_path: str = '.'):
        self._input_directory_path: str = os.path.join(project_directory_path, r'data');
        if not os.path.exists(self._input_directory_path): os.mkdir(self._input_directory_path);
        self._lazyFrame_files: dict[str, pl.LazyFrame] = {};


    # read_files(input_directory_path) both:
    #   A. Reads all _.parquet files.
    #   B. Reads ALL other files inside of the 'input_directory_path' and converts them into _.parquet files.
    # If a _.parquet file and another file share the same name, the OTHER file will NOT be read in to enable faster reading of data.
    def read_files(self) -> Self:
        entries: os._ScandirIterator = os.scandir(self._input_directory_path);
        entries = sorted(entries, key = lambda entry: entry.stat().st_mtime, reverse = True);

        for entry in entries:
            file_name: str = os.path.splitext(entry.name)[0];
            file_extension: str = os.path.splitext(entry.name)[1];
            if file_name in self._lazyFrame_files.keys(): continue;
            lazyFrame_file: pl.LazyFrame = None;

            if entry.name.endswith('.parquet'): lazyFrame_file = pl.scan_parquet(entry.path);
            else:                               lazyFrame_file = self._format_lazyFrame(entry.path); lazyFrame_file.sink_parquet(path = entry.path.replace(file_extension, '.parquet'));
            self._lazyFrame_files[file_name] = lazyFrame_file;
        return self;


    @abstractmethod
    # _format_lazyFrame(path) reformats the lazyFrame to correct conventions/dataTypes.
    def _format_lazyFrame(self, path: str) -> pl.LazyFrame:   pass


    def get_lazyFrame_files(self) -> dict[str, pl.LazyFrame]: return self._lazyFrame_files;



class COMPUSTAT__SECURITIES_DAILY(INPUT_DIRECTORY):
    def __init__(self, project_directory_path: str = '.'):
        super().__init__(project_directory_path);
        self._input_directory_path: str = os.path.join(self._input_directory_path, type(self).__name__);
        if not os.path.exists(self._input_directory_path):     print('INPUT CLASS DIRECTORY NOT FOUND!');    exit(1);
        elif len(os.listdir(self._input_directory_path)) == 0: print('INPUT CLASS DIRECTORY HAS NO FILES!'); 

    
    def _format_lazyFrame(self, path: str) -> pl.LazyFrame:
        #   1. Basic formatting: 
        lazyFrame_file: pl.LazyFrame = pl.scan_csv(path, infer_schema = False);
        lazyFrame_file = lazyFrame_file.rename({col: col.replace(' ', '_') for col in lazyFrame_file.collect_schema().names()});

        #   2. Defining column names & dataTypes
        column_dataTypes: dict[str, pl.Expr] = {
            'gvkey':    (pl.col('gvkey').cast(pl.Utf8)).alias('Global-Company-Key'),
            'conm':     (pl.col('conm').cast(pl.Utf8)).alias('Company-Name'),
            'datadate': (pl.col('datadate').str.to_date(format = '%Y-%m-%d')).alias('Date'),
            'tic':      (pl.col('tic').cast(pl.Utf8)).alias('Ticker'),
            'cshoc':    (pl.col('cshoc').cast(pl.UInt64)).alias('Shares-Outstanding'),
            'prccd':    (pl.col('prccd').cast(pl.Float64)).alias('Price-Close_Daily')
        };
        column_dataTypes = {col : column_dataTypes[col] for col in column_dataTypes.keys() if col in lazyFrame_file.collect_schema().names()};
        lazyFrame_file = lazyFrame_file.select(column_dataTypes.values());

        if ('Date' in lazyFrame_file.collect_schema().names()) & ('Ticker' in lazyFrame_file.collect_schema().names()): lazyFrame_file = lazyFrame_file.sort(by = ['Date', 'Ticker']);
        return lazyFrame_file;
