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
You will need a personal GitHub token (see instructions in `pbt-classification/README.md`). You will also need Python 3.12 and the Poetry dependency manager. 
To recreate the figures for the paper, run `pbt-classification/analysis/figures.ipynb` and `rq1.py`. Before running these, unzip the file `mutation-testing/data/results_w_cov_test.csv.zip`. 
To rerun the categorization of tests, follow the instructions in `pbt-classification/README.md` to collect the repositories and run the categorization code. To see the final percentages, run `rq1.py` again, changing the inputs to the functions to your new data files. 

## Step-by-Step Instructions
Follow all the instructions in the Getting Started guide. 

Then, to run new mutation tests, follow the instructions in `mutation-testing/README.md`. 
This will show how to run the scripts to download the repositories and run the mutation tests on them. 

These scripts download the repositories tested and apply any changes made to allow them to run properly. The commands used to run the mutation test for each individual project are also used. There is also a dependency requirements file which includes the Python dependencies of all the projects. Sometimes, issues with Python paths and module discoverability can come up, and these must be dealt with on a case-by-case basis. If you run into any of these, please contact the first author. 

## Reusability Guide
The `pbt-classification/hypothesis_analysis` part of this artifact can be reused. New tests can be classified using the existing setup, and additional categories can be added to the categorization code that is called by `pbt_detectors.py`. The mutation testing tool can be reused to run mutation tests for new projects (however, we note that it was forked from an [existing tool](https://github.com/boxed/mutmut)). 