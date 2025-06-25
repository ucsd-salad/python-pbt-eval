#!/bin/bash
set -e

LIST_FILE="mutation_testing_info_truncated.txt"

# poetry run pip install -e ./mutmut

while read -r name paths_to_mutate tests_dir runner; do
    PATHS_TO_MUTATE="$paths_to_mutate"
    TESTS_DIR="$tests_dir"
    RUNNER="$runner"
    cd repositories/"$name" || { echo "Directory $name not found!"; exit 1; }
    echo "Running mutation testing for $name"
    mutmut run --paths-to-mutate "$PATHS_TO_MUTATE" --tests-dir "$TESTS_DIR" --test-time-multiplier 2 --use-subset-size 100 --runner "$RUNNER"
    mutmut results
done < "$LIST_FILE"
 