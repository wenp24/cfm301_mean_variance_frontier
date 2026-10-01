from abc import ABC, abstractmethod
from typing_extensions import Self

import os
import polars as pl
import altair as alt

# OUTPUT.PY --- 
#   Handles all tasks related to outputting data.



class OUTPUT_DIRECTORY(ABC):
    def __init__(self, project_directory_path: str = '.'):
            # Resetting the log file
            self._log_path: str = os.path.join(project_directory_path, '_OUTPUT.txt');
            with open(self._log_path, 'w', encoding = 'utf-8') as log_file: pass;
            # Creating the directory path
            self._output_directory_path: str = os.path.join(project_directory_path, '_OUTPUT');
            if not os.path.exists(self._output_directory_path): os.mkdir(self._output_directory_path);
            # self._output_files is a dictionary which specifies:
            #   A. dict[str, ...]                              = The OUTPUT file_name.
            #   B. dict[..., tuple[str, ...] ]                 = The OUTPUT type
            #   C. dict[..., tuple[..., dict[str, str], ...] ] = Required arguments for the OUTPUT type.
            #   D. dict[..., tuple[..., ..., pl.LazyFrame] ]   = LazyFrame data to be output as a table OR data visualization.
            self._output_files: dict[str, tuple[str, dict[str, str], pl.LazyFrame] ] = {};


    @abstractmethod
    def create_files(self) -> Self: pass;


    def output_files(self) -> Self:
        for file_name, output in self._output_files.items():
            output_path: str            = os.path.join(self._output_directory_path, file_name);
            output_type: str            = output[0];
            output_args: dict[str, str] = output[1];
            output_data: pl.DataFrame   = output[2].collect();
            
            match (output_type):
                case 'default':
                    output_data.write_excel(
                        workbook = f'{output_path}.xlsx', worksheet = file_name, 
                        table_style = 'Table Style Medium 6',
                        include_header = True, autofilter = True, autofit = True, freeze_panes = (1,0)
                    );
                case 'lineByDate':
                    x_title: str = output_args['x'];
                    y_title: str = output_args['y'];
                    legend: str = output_args['legend'];

                    lineplot: alt.Chart = (
                        alt.Chart(output_data)
                        .mark_line(opacity = 0.3, tooltip = True)
                        .encode(
                            x = alt.X(f'{x_title}:T', axis = alt.Axis(format = '%Y-%m-%d', labelAngle = -90), title = x_title),
                            y = alt.Y(f'{y_title}:Q',                                                         title = y_title),
                            color = alt.Color(f'{legend}:N', sort = 'ascending',                              title = legend)
                        ).properties(width = 1000, height = 400, title = f'{y_title} by {x_title}')
                        .interactive()
                    );
                    lineplot.save(f'{output_path}.html');
                case 'scatterByDate':
                    x_title: str = output_args['x'];
                    y_title: str = output_args['y'];
                    legend: str = output_args['legend'];

                    scatterplot: alt.Chart = (
                        alt.Chart(output_data)
                        .mark_circle(size = 15, opacity = 0.3, tooltip = True)
                        .encode(
                            x = alt.X(f'{x_title}:T', axis = alt.Axis(format = '%Y-%m-%d', labelAngle = -90), title = x_title),
                            y = alt.Y(f'{y_title}:Q',                                                         title = y_title),
                            color = alt.Color(f'{legend}:N', sort = 'ascending',                              title = legend)
                        ).properties(width = 1000, height = 400, title = f'{y_title} by {x_title}')
                        .interactive()
                    );
                    scatterplot.save(f'{output_path}.html');
        return self;


    def _log_output(self, output: str | pl.DataFrame | pl.LazyFrame) -> None:
        with open(self._log_path, 'w', encoding = 'utf-8') as log_file:
            with pl.Config(fmt_str_lengths = 1000000, tbl_rows = -1, tbl_cols = -1):
                if isinstance(output, pl.LazyFrame): log_file.write(str(output.collect()));
                else:                                log_file.write(str(output));
