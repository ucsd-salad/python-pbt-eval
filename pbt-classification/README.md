# PBT Classification (RQ1)

## Instructions for Running the Code

### Environment Setup
We use the tool [Poetry](https://python-poetry.org/) to manage dependencies. Once Poetry is installed, run `poetry install` in the `hypothesis_analysis` directory to install all the project dependencies. 
GitHub requires usage of a personal access token in order to access multiple public repositories. To create this token, follow the instructions listed [here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens). Then, run `sh env_setup.sh` in the `hypothesis_analysis` directory to create a `.env` file. Then, add the personal access token you've created after `GITHUB_ACCESS_TOKEN=`. 


### Test Set Collection
To collect additional Python projects using Hypothesis for our test set, run the script in `new_corpus.sh`. The output will be in the CSV `cleaned_new_examples.csv` in the `corpus_test_set` directory. GitHub search may produce different values at each time. To account for this, we have provided our original test set we found in the directory `original_data` (`original_testset_detections.csv`). 


### Running the Test Classifiers
To run the detectors on the corpora, run `poetry run python collect_data.py` in the `hypothesis_analysis` directory. This will produce a CSV (`detections_0-1587.csv`). To calculate the percentages of each category, run `poetry run python rq1.py`. Because the program retrieves the current state of the repository, some may no longer exist, and the resulting percentages may differ from the paper. We have also included the classification data used in the original paper to compare (`original_detections.csv`). 


## List of Contents 
The contents of this portion of the artifact broken down by directory. 

- `hypothesis_analysis/`
    - Python code for parsing an categorizing property-based-tests 
- `corpus/`
    - list of projects that use the Hypothesis library 
- `data/artifact_eval`
    - where the test classificaton data will be stored
- `analysis`
    - scripts for the analysis of the data

