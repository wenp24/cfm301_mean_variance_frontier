from abc import ABC, abstractmethod
from typing_extensions import Self

import os
import polars as pl
import altair as alt

# OUTPUT.PY --- 
#   Handles all tasks related to outputting data.



class OUTPUT_DIRECTORY(ABC):
    def __init__(self, project_directory_path: str = '.'):
            # Resetting the log and error files
            self._log_path: str = os.path.join(project_directory_path, '_OUTPUT.txt');
            with open(self._log_path, 'w', encoding = 'utf-8') as log_file: pass;
            self._error_path: str = os.path.join(project_directory_path, '_ERROR.txt');
            with open(self._error_path, 'w', encoding = 'utf-8') as log_file: pass;
            # Creating the directory path
            self._output_directory_path: str = os.path.join(project_directory_path, '_OUTPUT');
            if not os.path.exists(self._output_directory_path): os.mkdir(self._output_directory_path);
            # self._output_files is a dictionary which specifies:
            #   A. dict[str, ...]                                       = The OUTPUT file_name.
            #   B. dict[..., tuple[str, ...] ]                          = The OUTPUT type
            #   C. dict[..., tuple[..., dict[str, str], ...] ]          = Required arguments for the OUTPUT type.
            #   D. dict[..., tuple[..., ..., dict[str, pl.LazyFrame]] ] = Dictionary of lazyFrame data TO BE OUTPUT as a table OR data visualization.
            self._output_files: dict[str, tuple[str, dict[str, str], dict[str, pl.LazyFrame]] ] = {};


    @abstractmethod
    def create_files(self) -> Self: pass;


    def output_files(self) -> Self:
        for file_name, output in self._output_files.items():
            output_path: str                         = os.path.join(self._output_directory_path, file_name);
            output_type: str                         = output[0];
            output_args: dict[str, str]              = output[1];
            output_dataDict: dict[str, pl.DataFrame] = output[2];
            
            match (output_type):
                case 'default':
                    output_data: pl.DataFrame = output_dataDict['Main'].collect();

                    output_data.write_excel(
                        workbook = f'{output_path}.xlsx', worksheet = file_name, 
                        table_style = 'Table Style Medium 6',
                        include_header = True, autofilter = True, autofit = True, freeze_panes = (1,0)
                    );
                case 'line':
                    output_data: pl.DataFrame = output_dataDict['Main'].collect();
                    x_title: str = output_args['x'];
                    y_title: str = output_args['y'];
                    legend: str = output_args['legend'];
                    if (output_data[x_title].dtype == pl.Date): x_axis = alt.X(f'{x_title}:T', axis = alt.Axis(format = '%Y-%m-%d', labelAngle = -90), title = x_title);
                    else:                                       x_axis = alt.X(f'{x_title}:Q', title = x_title);

                    lineplot: alt.Chart = (
                        alt.Chart(output_data)
                        .mark_line(opacity = 0.3, tooltip = True)
                        .encode(
                            x = x_axis,
                            y = alt.Y(f'{y_title}:Q',                            title = y_title),
                            color = alt.Color(f'{legend}:N', sort = 'ascending', title = legend)
                        ).properties(width = 1000, height = 400, title = f'{y_title} by {x_title}')
                        .interactive()
                    );
                    lineplot.save(f'{output_path}.html');
                case 'scatter':
                    output_data: pl.DataFrame = output_dataDict['Main'].collect();
                    x_title: str = output_args['x'];
                    y_title: str = output_args['y'];
                    legend: str = output_args['legend'];
                    if (output_data[x_title].dtype == pl.Date): x_axis = alt.X(f'{x_title}:T', axis = alt.Axis(format = '%Y-%m-%d', labelAngle = -90), title = x_title);
                    else:                                       x_axis = alt.X(f'{x_title}:Q', title = x_title);

                    scatterplot: alt.Chart = (
                        alt.Chart(output_data)
                        .mark_circle(size = 15, opacity = 0.3, tooltip = True)
                        .encode(
                            x = x_axis,
                            y = alt.Y(f'{y_title}:Q',                            title = y_title),
                            color = alt.Color(f'{legend}:N', sort = 'ascending', title = legend)
                        ).properties(width = 1000, height = 400, title = f'{y_title} by {x_title}')
                        .interactive()
                    );
                    scatterplot.save(f'{output_path}.html');
                case 'meanVarianceFrontier':
                    random_data:   pl.DataFrame = output_dataDict['Random'].collect();
                    x_scatterTitle: str = output_args['xScatter'];
                    y_scatterTitle: str = output_args['yScatter'];
                    random_data = random_data.with_row_index(name = 'scatterLegend', offset = 1);
                    random_data = random_data.with_columns((pl.format('Portfolio-{}', pl.col('scatterLegend'))).alias('scatterLegend'));
                    frontier_data: pl.DataFrame = output_dataDict['Frontier'].collect();
                    x_lineTitle: str = output_args['xLine'];
                    y_lineTitle: str = output_args['yLine'];

                    scatterplot: alt.Chart = (
                        alt.Chart(random_data)
                        .mark_circle(size = 15, opacity = 0.3)
                        .encode(
                            x = alt.X(f'{x_scatterTitle}:Q',                          title = x_scatterTitle),
                            y = alt.Y(f'{y_scatterTitle}:Q',                          title = y_scatterTitle),
                            color = alt.Color(f'scatterLegend:N', sort = 'ascending', title = legend)
                        )
                    );
                    lineplot: alt.Chart = (
                         alt.Chart(frontier_data)
                         .mark_line(size = 2, strokeDash = [2 ,4], color = 'black')
                         .encode(
                              x = alt.X(f'{x_lineTitle}:Q', title = x_lineTitle),
                              y = alt.Y(f'{y_lineTitle}:Q', title = y_lineTitle),
                         )   
                    );
                    dataplot: alt.Chart = (
                         (scatterplot + lineplot)
                         .properties(width = 1000, height = 400, title = f'Standard-Deviation by Expected-Return')
                         .interactive()
                    );
                    dataplot.save(f'{output_path}.html');
        return self;


    def _log_output(self, output: str | pl.DataFrame | pl.LazyFrame) -> None:
        with open(self._log_path, 'a', encoding = 'utf-8') as log_file:
            with pl.Config(fmt_str_lengths = 1000000, tbl_rows = -1, tbl_cols = -1):
                if isinstance(output, pl.LazyFrame): log_file.write(f'{output.collect()}\n\n');
                else:                                log_file.write(f'{output}\n\n');


    def _log_error(self, output: str | pl.DataFrame | pl.LazyFrame) -> None:
            with open(self._error_path, 'a', encoding = 'utf-8') as log_file:
                with pl.Config(fmt_str_lengths = 1000000, tbl_rows = -1, tbl_cols = -1):
                    if isinstance(output, pl.LazyFrame): log_file.write(f'{output.collect()}\n\n');
                    else:                                log_file.write(f'{output}\n\n');
