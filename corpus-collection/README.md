# Boa Instructions
To obtain the corpus of projects, we used the [Boa](https://boa.cs.iastate.edu) infrastructure to query a dataset of GitHub Python repositories. 
As of June 23, 2025, the Boa site is down, so skip to the Data Cleanup step using the `boa-job107852-output.txt` file. 

## Using Boa

Copy over the code from the `corpus-collection/hypothesis_imports.boa` file to the tool and run it on the Github Python 2022 dataset. After the code is run, a job output file will be created. 

## Data Cleanup

To create the CSV of repositories, change the value of `boa_file` on line 23 of `cleanup_data.py` to the name of the output file. This will produce a CSV `hypothesis_imports_raw.csv`. 

There is another popular Python repository called Hypothesis, and some of the entries in the CSV will not be true uses of the PBT library Hypothesis. To filter out these instances, we first filtered by those with namespaces that contain the word "test" and then manually inspected the instances that did not contain the word "test" to see if they were actual uses of Hypothesis. This portion was done on Google Sheets by importing the CSV, naming that sheet `hypothesis_imports` and using the formula `=filter(hypothesis_imports!1:2285,not(regexmatch(lower(hypothesis_imports!C:C),"test")))` to remove the entries that do not contain the word "test". The CSV containing the namespaces without the word "test" is `gsheet_hypothesis_imports_non_test.csv`, and the final, cleaned-up CSV is included under the name `hypothesis_imports.csv`. This CSV will be used in the rest of the artifact. 