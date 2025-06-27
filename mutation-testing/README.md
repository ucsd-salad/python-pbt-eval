# Mutation Testing (RQ2 and RQ3)

## Setup
Install Poetry (see README for `pbt-classification/`) and run `poetry install`. 
Run `download_repositories` to download the tested repositories and add the diffs. 
Then, run `poetry run pip install -r requirements_for_repos.txt` to add all the dependencies for each of the repositories. In rare cases, some versions will contradict between repositories. Please contact me if you run into any issues with this. 
Changes were made to the repositories (as seen in the diffs) to accomodate features of the cluster we conducted mutation testing on. As a result, some additional changes may be required to make these run on other machines such as fixing paths to the Python interpreter. Again, please contact me if you face any problems relating to this. 

## Mutation Testing
To run the mutation tests, run `run_mutation_testing.sh`. This will print the output of each mutation test to stdout. If you do not wish to test all 100 mutations, then `choose-subset-size` can be changed to something smaller (such as 10). Mutation testing is computationally intensive, and running 100 mutations for one project can take 1-5 hours depending on the repository. Note: the mutations are randomly selected from all the possible mutations that can be made to a project. To run fewer projects, truncate the list of repositories in `mutation_testing_info.txt`. 

## Parameter Sweep
To run the parameter sweep experiment, remove `hypothesis` as a dependency, and instead install the local version of Hypothesis through `poetry add ./hypothesis`. This will force Hypothesis to use 500 inputs to each test (when possible). Then, rerun the mutation testing following the steps above. This version of Hypothesis also reports timing data for each test (for which we also include our original data). 

## Statistics
The Chi-square and logistic regression statistics were found using the software JMP, for which there is a [free trial](linktotrial). We have included the CSV that was uploaded into JMP (`data/results_w_cov_test.csv`). The figures in the paper can be recreated by running the Jupyter notebook in the `pbt-classification/analysis` folder. 

