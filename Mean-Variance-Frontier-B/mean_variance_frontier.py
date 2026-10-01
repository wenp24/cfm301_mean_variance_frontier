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
        for key, lazyFrame in self.__compustat_securitesDaily.items(): self.__compustat_securitesDaily[key] = lazyFrame.filter(pl.col('Date').is_between(pl.date(2020,  1,  1), pl.date(2026,  9,  1)));


    def create_files(self) -> Self:
        self.__check_data();
        self.__edit_data();
        return self;


    # __check_data() makes sure that the data from the ABOVE parameter objects are ready for computational analysis.
    # EX: compustat_securitiesDaily(...)
    def __check_data(self) -> None:
        # FUNCTIONS FOR CLEANING DATA ---
        def exist_inactiveTickers() -> bool:
            #   1. Obtaining the RANGE of dates in which the tickers were active.
            allTickers_dateRange: pl.LazyFrame = (
                lazyFrame
                .group_by('Ticker', maintain_order = True)
                .agg([
                    (pl.col('Date').min()).alias('Date_Start'), (pl.col('Date').max()).alias('Date_End'),
                    (pl.col('Date').len()).alias('Days_Active')
                ])
            );
            #   2. FILTER OUT the ACTIVE tickers to obtain the INACTIVE tickers.
            inactiveTickers: pl.LazyFrame = allTickers_dateRange.filter(pl.col('Days_Active') != pl.col('Days_Active').mode());
            #       A. Return TRUE if inactiveTickers NOT EMPTY
            #       B. Return FALSE if inactiveTickers is EMPTY
            if (inactiveTickers.select(pl.len()).collect().item() > 0): return True;
            else:                                                       return False;

        # RUNNING CLEAN_DATA() --- 
        for key, lazyFrame in self.__compustat_securitesDaily.items():
            # PROGRAMATIC CHECKS ---
            if exist_inactiveTickers(): print('INACTIVE TICKERS FOUND!');  exit(1);

            # MANUAL CHECKS ---
            #   - Checking for no stock splits...
            #       1. For State-Street...
            #               A. Date: 2025-12-05
            #                  Ticker(s): XLK, XLU
            #                  Stock-Splits: 2-1
            #       2. For A.I. infrastructure...
            #           Using the 'Scatterplot' & Google, we found the following stock splits:
            #               A. Date:         2021-07-20         D. Date:         2024-07-15
            #                  Ticker:       NVDA                  Ticker:       AVGO
            #                  Stock-Splits: 4-1                   Stock-Splits: 10-1
            #               B. Date:         2021-11-18         E. Date:         2024-12-04
            #                  Ticker:       ANET                  Ticker:       ANET
            #                  Stock-Splits: 4-1                   Stock-Splits: 4-1
            #               C. Date:         2024-06-10
            #                  Ticker:       NVDA
            #                  Stock-Splits: 10-1
            self._output_files[f'{key}_LINEPLOT'] = ('lineByDate', { 'x': 'Date', 'y': 'Price-Close_Daily', 'legend': 'Ticker' }, lazyFrame);
        return None;


    # __edit_data() fixes any earlier issues found in __check_data().
    def __edit_data(self) -> None:
        for key, lazyFrame in self.__compustat_securitesDaily.items():
            # Adjusting the ABOVE stock-splits.
            if key == 'State-Street':
                self.__compustat_securitesDaily[key] = (
                    lazyFrame
                    .with_columns((pl.when((pl.col('Ticker').is_in(['XLK', 'XLU'])) & (pl.col('Date') < pl.date(2025, 12,  5))).then(pl.col('Price-Close_Daily')  / 2 ).otherwise(pl.col('Price-Close_Daily'))).alias('Price-Close_Daily'))
                );
            elif key == 'AI-Infrastructure':
                self.__compustat_securitesDaily[key] = (
                    lazyFrame
                    .with_columns([
                        (pl.when((pl.col('Ticker') == 'NVDA') & (pl.col('Date') < pl.date(2021,  7, 20))).then(pl.col('Shares-Outstanding') * 4 ).otherwise(pl.col('Shares-Outstanding'))).alias('Shares-Outstanding'),
                        (pl.when((pl.col('Ticker') == 'NVDA') & (pl.col('Date') < pl.date(2021,  7, 20))).then(pl.col('Price-Close_Daily')  / 4 ).otherwise(pl.col('Price-Close_Daily'))).alias('Price-Close_Daily')
                    ]).with_columns([
                        (pl.when((pl.col('Ticker') == 'ANET') & (pl.col('Date') < pl.date(2021, 11, 18))).then(pl.col('Shares-Outstanding') * 4 ).otherwise(pl.col('Shares-Outstanding'))).alias('Shares-Outstanding'),
                        (pl.when((pl.col('Ticker') == 'ANET') & (pl.col('Date') < pl.date(2021, 11, 18))).then(pl.col('Price-Close_Daily')  / 4 ).otherwise(pl.col('Price-Close_Daily'))).alias('Price-Close_Daily')
                    ]).with_columns([
                        (pl.when((pl.col('Ticker') == 'NVDA') & (pl.col('Date') < pl.date(2024,  6, 10))).then(pl.col('Shares-Outstanding') * 10).otherwise(pl.col('Shares-Outstanding'))).alias('Shares-Outstanding'),
                        (pl.when((pl.col('Ticker') == 'NVDA') & (pl.col('Date') < pl.date(2024,  6, 10))).then(pl.col('Price-Close_Daily')  / 10).otherwise(pl.col('Price-Close_Daily'))).alias('Price-Close_Daily')
                    ]).with_columns([
                        (pl.when((pl.col('Ticker') == 'AVGO') & (pl.col('Date') < pl.date(2024,  7, 15))).then(pl.col('Shares-Outstanding') * 10).otherwise(pl.col('Shares-Outstanding'))).alias('Shares-Outstanding'),
                        (pl.when((pl.col('Ticker') == 'AVGO') & (pl.col('Date') < pl.date(2024,  7, 15))).then(pl.col('Price-Close_Daily')  / 10).otherwise(pl.col('Price-Close_Daily'))).alias('Price-Close_Daily')
                    ]).with_columns([
                        (pl.when((pl.col('Ticker') == 'ANET') & (pl.col('Date') < pl.date(2024, 12,  4))).then(pl.col('Shares-Outstanding') * 4 ).otherwise(pl.col('Shares-Outstanding'))).alias('Shares-Outstanding'),
                        (pl.when((pl.col('Ticker') == 'ANET') & (pl.col('Date') < pl.date(2024, 12,  4))).then(pl.col('Price-Close_Daily')  / 4 ).otherwise(pl.col('Price-Close_Daily'))).alias('Price-Close_Daily')
                    ])
                );
            self._output_files[f'{key}_LINEPLOT-EDITED'] = ('lineByDate', { 'x': 'Date', 'y': 'Price-Close_Daily', 'legend': 'Ticker' }, self.__compustat_securitesDaily[key]);
        return None;
