import time

from input import COMPUSTAT__SECURITIES_DAILY
from mean_variance_frontier import MEAN_VARIANCE_FRONTIER

# MAIN.PY ---
#   Hub where all functions are run and cursory changes are made.
#   EX: Changing the file-path parameters of an INPUT class

project_directory_path: str = r'C:\Users\Justin Yi Cheng\UWaterloo\CFM 301\Project-1\cfm301_mean_variance_frontier\Mean-Variance-Frontier-B';



def main():
    #   1. Instantiating the INPUT classes
    compustat_securitiesDaily = COMPUSTAT__SECURITIES_DAILY(project_directory_path = project_directory_path);

    #   2. Instantiating OUTPUT classes
    mean_variance_frontier = MEAN_VARIANCE_FRONTIER(compustat_securitiesDaily = compustat_securitiesDaily, 
                                                    project_directory_path = project_directory_path);

    #   3. Running main()...
    mean_variance_frontier.create_files().output_files();
    return;



if __name__ == '__main__':
    start_time: float = time.time();
    
    main();
    
    print(f'Runtime: {round(time.time() - start_time, 5)} Seconds');

