# python-pbt-eval
The artifact associated with the paper "An Empirical Evaluation of Property-Based Testing in Python" for OOPSLA 2025.
The code for answering RQ1 is found in the sub-folder `pbt-classification/` and its associated `README.md` file. 
The code for answering RQ2 and RQ3 is found in the `mutation-testing/` sub-directory along with directions.  

## Introduction

The purpose of this artifact is to provide the code for the PBT test classification, and the data analysis of the results of mutation testing. 

### Claims:
- RQ1 Result: The most common PBTs in our corpora include PBTs checking equality with constants (41%, 39% in test set), commutative paths (24%, 14%), and roundtrips (7%, 29%). In addition, 94% of our corpus was categorized with our tool (however this may be fully supported due to repositories being taken offline since the work was done)
- RQ2 Result: Unit tests comprised 98.4% of our sample and killed 84.7% of the total mutations found, while PBTs (comprising 1.6%) killed 15.3% of mutations. On a per-test basis, property-based tests were more effective at catching mutations than unit tests. Exception raising, inclusion, and type checking were the most effective of the property-based test categories.
- RQ3 Result: Over half of the mutations (55%) were found with a single input to a PBT. 76% of mutations were found within the first 20 inputs to a PBT function, 86% within the first 100 inputs, and 96% within the first 350 inputs.

We believe these claims can be supported by this artifact when using our original results. When retrieving new data, there may be some differences in the numbers. 

## Hardware Dependencies

There are no hardware dependencies for all parts of the project, except if one chooses to rerun the mutation testing. It is possible to run mutation testing on a few projects on a typical laptop (which will take a few hours), but in order to run the mutation tests for all projects, we recommend using a cluster with one machine per project. 

## Getting Started
You will need a personal GitHub token, Python 3.12, and the Poetry dependency manager (see instructions below for environment setup). 
To recreate the figures for the paper, run `pbt-classification/analysis/figures.ipynb` as a Jupyter notebook and `poetry run python analysis/rq1.py` from the `pbt-classification` directory. Before running these, unzip the file `mutation-testing/data/results_w_cov_test.csv.zip`. 
To rerun the categorization of tests, follow the instructions in `pbt-classification/README.md` to collect the repositories and run the categorization code. To see the final percentages, run `rq1.py` again, changing the inputs to the functions to your new data files. 
For more details, follow the step-by-step instructions below. 

## Environment Setup
We use the tool [Poetry](https://python-poetry.org/) to manage dependencies. Once Poetry is installed, run `poetry install` in the `pbt-classification` directory to install all the project dependencies. 
GitHub requires usage of a personal access token in order to access multiple public repositories. To create this token, follow the instructions listed [here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens). Then, run `sh env_setup.sh` in the `pbt-classification` directory to create a `.env` file also in the `pbt-classification` directory. Then, add the personal access token you've created after `GITHUB_ACCESS_TOKEN=`. We also use the GitHub CLI to collect repositories, so please install the [CLI](https://cli.github.com/) according to the instructions given on the site. 

## Step-by-Step Instructions

### Corpus Collection
Follow the instructions in [`corpus-collection/README.md`](corpus-collection/README.md) to collect the corpus used in the evaluation. We also include the final corpus we used in [`corpus-collection/hypothesis_imports.csv](corpus-collection/hypothesis_imports.csv). 

#### Test Set Collection
To collect additional Python projects using Hypothesis for our test set, run the script in `pbt-classification/corpus/new_corpus.sh`. The output will be in the CSV `cleaned_new_examples.csv` in the `pbt-classification/corpus` directory. GitHub search may produce different values at each time. To account for this, we have provided our original test set we found in the directory [`original_data`](pbt-classification/original_data/original_testset_detections.csv). 

### Recreating Figures and Running Test Classifiers
To recreate the figures for the paper, run `pbt-classification/analysis/figures.ipynb` as a Jupyter notebook and `poetry run python analysis/rq1.py` from the `pbt-classification` directory. Before running these, unzip the file `mutation-testing/data/results_w_cov_test.csv.zip`. 

To run the detectors on the corpora, run `poetry run python hypothesis_analysis/collect_data.py` in the `pbt-classification` directory. This will produce a CSV (`detections_0-1587.csv`). To calculate the percentages of each category, run `poetry run python analysis/rq1.py` in the `pbt-classification` directory. Because the program retrieves the current state of the repository, some may no longer exist, and the resulting percentages may differ from the paper. We have also included the classification data used in the original paper to compare (`original_detections.csv`). 

To rerun the categorization of tests, follow the instructions above to collect the repositories and run the categorization code. To see the final percentages, run `rq1.py` again, changing the inputs to the functions to your new data files. 

### Mutation Testing
To run new mutation tests, follow the instructions in `mutation-testing/README.md`. 
This will show how to run the scripts to download the repositories and run the mutation tests on them. 

These scripts download the repositories tested and apply any changes made to allow them to run properly. The commands used to run the mutation test for each individual project are also used. There is also a dependency requirements file which includes the Python dependencies of all the projects. Sometimes, issues with Python paths and module discoverability can come up, and these must be dealt with on a case-by-case basis. If you run into any of these, please contact the first author. 

## Reusability Guide
The `pbt-classification/hypothesis_analysis` part of this artifact can be reused. New tests can be classified using the existing setup, and additional categories can be added to the categorization code that is called by `pbt_detectors.py`. The mutation testing tool can be reused to run mutation tests for new projects (however, we note that it was forked from an [existing tool](https://github.com/boxed/mutmut)). This work is also dependent on Hypothesis version 6.13. 