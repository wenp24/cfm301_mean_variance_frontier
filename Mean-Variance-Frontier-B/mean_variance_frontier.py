from typing_extensions import Self, final

import os
import numpy as np
import pandas as pd
import polars as pl
import scipy.optimize as sco

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
        # FUNCTIONS FOR CREATE_FILE() ---
        def get_meanReturns(lazyFrame: pl.LazyFrame) -> pd.DataFrame:
            mean_returns: pd.DataFrame = (
                lazyFrame
                .group_by('Ticker', maintain_order = True)
                .agg((pl.col('Price-Close_Daily').pct_change().mean()).alias('Mean_Return'))
                .collect()
                .to_pandas()
            );
            mean_returns.set_index('Ticker', inplace = True);
            return mean_returns;
        def get_covarianceMatrix(lazyFrame: pl.LazyFrame) -> pd.DataFrame:
            covariance_matrix: pd.DataFrame = (
                lazyFrame
                .pivot(on = 'Ticker', index = 'Date', on_columns = all_tickers, values = 'Price-Close_Daily', maintain_order = True)
                .with_columns(pl.col(pl.Float64).pct_change())
                .drop_nulls()
                .collect()
                .to_pandas()
            );
            covariance_matrix.set_index('Date', inplace = True);
            covariance_matrix = covariance_matrix.cov();
            return covariance_matrix;


        # RUNNING CREATE_FILE() ---
        #   1. Checking / Cleaning the data
        self.__check_data();
        self.__edit_data();

        #   2. Finding the Mean-Returns / Covariance_Matrixes
        ticker_minSTD: dict[str, tuple] = {};
        for key, lazyFrame in self.__compustat_securitesDaily.items():
            if key == 'AI-Infrastructure':
                lazyFrame: pl.LazyFrame = (
                    lazyFrame
                    .with_columns((pl.col('Shares-Outstanding').over('Date') / pl.col('Shares-Outstanding').sum().over('Date')).alias('Portfolio-Weight'))
                    .with_columns((pl.col('Portfolio-Weight') * pl.col('Price-Close_Daily')).alias('Price-Close_Daily'))
                    .with_columns(pl.col('Price-Close_Daily').sum().over('Date'))
                );
                self._log_output(lazyFrame);
            # all_tickers: pl.DataFrame = lazyFrame.select(pl.col('Ticker').unique().sort()).collect();
            # mean_returns: pd.DataFrame = None;
            # covariance_matrix: pd.DataFrame = None;

            # if key == 'State-Street':
            #     mean_returns = get_meanReturns(lazyFrame = lazyFrame);
            #     covariance_matrix = get_covarianceMatrix(lazyFrame = lazyFrame);
            # elif key == 'AI-Infrastructure':

            # ticker_minSTD[key] = self.__create_meanVarianceFrontier(key = key, mean_returns = mean_returns, covariance_matrix = covariance_matrix);
        for key, minSTD in ticker_minSTD.items(): print(f'{key} has a minimum standard-deviation of {round(minSTD[0], 4)} and correlated expected-return of {round(minSTD[1], 4)}');
        return self;


    # __check_data() makes sure that the data from the ABOVE parameter objects are ready for computational analysis.
    # EX: compustat_securitiesDaily(...)
    def __check_data(self) -> None:
        # FUNCTIONS FOR CHECK_DATA() ---
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
            #       A. Return TRUE  if inactiveTickers NOT EMPTY
            #       B. Return FALSE if inactiveTickers is EMPTY
            if (inactiveTickers.select(pl.len()).collect().item() > 0): return True;
            else:                                                       return False;

        # RUNNING CHECK_DATA() --- 
        for key, lazyFrame in self.__compustat_securitesDaily.items():
            # PROGRAMATIC CHECKS ---
            if exist_inactiveTickers(): print('INACTIVE TICKERS FOUND!');  exit(1);

            # MANUAL CHECKS ---
            #   - Checking for stock splits...
            #       1. For State-Street, found...
            #               A. Date: 2025-12-05
            #                  Ticker(s): XLK, XLU
            #                  Stock-Splits: 2-1
            #       2. For A.I. infrastructure, found...
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
            self._output_files[f'{key}_LINEPLOT'] = ('line', { 'x': 'Date', 'y': 'Price-Close_Daily', 'legend': 'Ticker' }, { 'Main': lazyFrame });
        return None;


    # __edit_data() fixes any earlier issues found in __check_data().
    def __edit_data(self) -> None:
        # RUNNING EDIT_DATA() ---
        for key, lazyFrame in self.__compustat_securitesDaily.items():
            # Adjusting the ABOVE stock-splits from __check_data().
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
            self._output_files[f'{key}_EDITED'] = ('default', {}, { 'Main': self.__compustat_securitesDaily[key] });    
            self._output_files[f'{key}_LINEPLOT_EDITED'] = ('line', { 'x': 'Date', 'y': 'Price-Close_Daily', 'legend': 'Ticker' }, { 'Main': self.__compustat_securitesDaily[key] });
        return None;


    def __create_meanVarianceFrontier(self, key: str, mean_returns: pd.DataFrame, covariance_matrix: pd.DataFrame) -> tuple:
        # FUNCTIONS FOR CREATE_MEANVARIANCEFRONTIER() ---
        #   - generate_randomPortfolios(num_portfolios, mean_returns, covariance_matrix) creates a lazyFrame of Annualized_Expected-Returns / Annualized_Standard-Deviations 
        #     based on a set of random weights.
        def generate_randomPortfolios(num_portfolios: int, mean_returns: pd.DataFrame, covariance_matrix: pd.DataFrame) -> pl.LazyFrame:            
            random_portfolios: dict[str, list] = {'Weights': [], 'Annualized_Expected-Return': [], 'Annualized_Standard-Deviation': []};

            for _ in range(0, num_portfolios, 1):
                weights: np.NDArray[np.float64] = np.random.random(num_tickers);
                weights = weights / np.sum(weights);
                annualized_expectedReturn: float = ((weights @ mean_returns) * 252).item();
                annualized_standardDeviation: float = np.sqrt(weights.T @ covariance_matrix @ weights) * np.sqrt(252);

                random_portfolios['Weights'].append(weights);
                random_portfolios['Annualized_Expected-Return'].append(annualized_expectedReturn);
                random_portfolios['Annualized_Standard-Deviation'].append(annualized_standardDeviation);
            random_portfolios: pl.LazyFrame = pl.LazyFrame(random_portfolios);
            return random_portfolios;
        #   - generate_efficientFrontier(mean_returns, covariance_matrix, target_range) takes a range of targets and determines the weights 
        #     required to obtain the MINIMUM variance for a range of target expected returns.
        def generate_efficientFrontier(mean_returns: pd.DataFrame, covariance_matrix: pd.DataFrame, target_range: np.ndarray) -> pl.LazyFrame:
            def find_efficientReturn(target: float) -> sco.OptimizeResult:
                def portfolio_expectedReturn(weights: np.NDArray[np.float64], mean_returns: pd.DataFrame):         return ((weights @ mean_returns) * 252).item();
                def portfolio_standardDeviation(weights: np.NDArray[np.float64], covariance_matrix: pd.DataFrame): return np.sqrt(weights.T @ covariance_matrix @ weights) * np.sqrt(252);
                args: tuple = (covariance_matrix,);
                constraints: tuple = ({'type': 'eq', 'fun': lambda x: portfolio_expectedReturn(x, mean_returns = mean_returns) - target},
                                      {'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
                bounds: tuple[tuple] = tuple((0.0, 1.0) for ticker in range(num_tickers));
                result = sco.minimize(portfolio_standardDeviation, num_tickers * [1./num_tickers,], args = args, method = 'SLSQP', bounds = bounds, constraints = constraints);
                return result;

            efficientReturns: dict[str, float] = {'Annualized_Expected-Return': [], 'Annualized_Standard-Deviation': []};
            for target in target_range:
                result: sco.OptimizeResult = find_efficientReturn(target);
                if result['success'] == False: continue;
                efficientReturns['Annualized_Expected-Return'].append(target); 
                efficientReturns['Annualized_Standard-Deviation'].append(result['fun']);
            efficientReturns: pl.LazyFrame = pl.LazyFrame(efficientReturns);
            return efficientReturns;


        # RUNNING CREATE_MEANVARIANCEFRONTIER() ---
        num_tickers: int = len(mean_returns);

        randomPortfolio: pl.LazyFrame = generate_randomPortfolios(25000, mean_returns, covariance_matrix);
        target_start: int = randomPortfolio.filter(pl.col('Annualized_Standard-Deviation') == pl.col('Annualized_Standard-Deviation').min()).select('Annualized_Expected-Return').collect().item();
        target_stop: int = randomPortfolio.filter(pl.col('Annualized_Standard-Deviation') == pl.col('Annualized_Standard-Deviation').max()).select('Annualized_Expected-Return').collect().item();
        efficientFrontier: pl.LazyFrame = generate_efficientFrontier(mean_returns = mean_returns, covariance_matrix = covariance_matrix, target_range = np.linspace(start = target_start, stop = target_stop, num = 100));
        minSTD_standardDeviation: float = efficientFrontier.select(pl.col('Annualized_Standard-Deviation').min()).collect().item();
        minSTD_expectedReturn:    float = efficientFrontier.filter(pl.col('Annualized_Standard-Deviation') == pl.col('Annualized_Standard-Deviation').min()).select('Annualized_Expected-Return').collect().item();    
        self._output_files[f'{key}_Mean-Variance-Frontier'] = ('meanVarianceFrontier', { 'xScatter': 'Annualized_Standard-Deviation', 'yScatter': 'Annualized_Expected-Return', 'xLine': 'Annualized_Standard-Deviation', 'yLine': 'Annualized_Expected-Return' }, { 'Random': randomPortfolio, 'Frontier': efficientFrontier });
        return (minSTD_standardDeviation, minSTD_expectedReturn);
