from typing_extensions import Self, final

import os
import polars as pl

from input import COMPUSTAT__SECURITIES_DAILY
from output import OUTPUT_DIRECTORY



@final
class MEAN_VARIANCE_FRONTIER(OUTPUT_DIRECTORY):
    def __init__(self, compustat_securitiesDaily: COMPUSTAT__SECURITIES_DAILY, 
                 project_directory_path: str = '.'):
        super().__init__(project_directory_path);
        self._output_directory_path: str = os.path.join(self._output_directory_path, type(self).__name__);
        if os.path.exists(self._output_directory_path): [os.unlink(os.path.join(self._output_directory_path, file)) for file in os.listdir(self._output_directory_path)];
        else:                                           os.mkdir(self._output_directory_path);

        self.__compustat_securitesDaily: dict[str, pl.LazyFrame] = compustat_securitiesDaily.read_files().get_lazyFrame_files();


    def create_files(self) -> Self:
        self.__clean_data();
        return self;


    def __clean_data(self) -> None:
        # FUNCTIONS FOR CLEANING DATA ---
        def find_inactiveTickers() -> pl.LazyFrame:
            #   1. Obtaining the RANGE of dates in which the tickers were active.
            allTickers_dateRange: pl.LazyFrame = (
                lazyFrame
                .group_by('Ticker', maintain_order = True)
                .agg([
                    (pl.col('Date').min()).alias('Date_Start'), (pl.col('Date').max()).alias('Date_End'),
                    (pl.col('Date').len()).alias('Days_Active')
                ])
            );
            #   2. Filter out the ACTIVE tickers to obtain the INACTIVE tickers.
            inactiveTickers: pl.LazyFrame = allTickers_dateRange.filter(pl.col('Days_Active') != pl.col('Days_Active').mode());
            return inactiveTickers;


        # RUNNING CLEAN_DATA() --- 
        for lazyFrame in self.__compustat_securitesDaily.values():
            inactiveTickers: pl.LazyFrame = find_inactiveTickers();
            self._output_files['TEMP_SCATTERPLOT'] = ('scatterByDate', { 'x': 'Date', 'y': 'Price-Close_Daily', 'legend': 'Ticker'  }, lazyFrame);
              
            # print(daysActive_mode);
            # self._log_output(ticker_dateRange);  
        
        return None;
