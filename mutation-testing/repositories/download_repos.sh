#!/bin/bash

REPO_LIST="repository_urls_truncated.txt"
#TODO change back to untruncated version

if [[ ! -f "$REPO_LIST" ]]; then
    echo "File $REPO_LIST not found!"
    exit 1
fi

while IFS=, read -r url hash || [[ -n "$url" ]]; do
    # Skip empty or whitespace-only lines
    [[ -z "${url// }" ]] && continue
    repo_dir=$(basename "$url" .git)
    if [[ -d "$repo_dir" ]]; then
        echo "Repository $repo_dir already exists, skipping clone."
    else
        git clone "$url"
    fi
    if [[ -d "$repo_dir" ]]; then
        pushd "$repo_dir" > /dev/null
        git reset --hard "$hash"
        popd > /dev/null
    else
        echo "Failed to clone $url"
    fi
done < "$REPO_LIST"

DIFF_DIR="diffs"

if [[ ! -d "$DIFF_DIR" ]]; then
    echo "Diff directory $DIFF_DIR not found!"
    exit 1
fi

for diff_file in "$DIFF_DIR"/*.diff; do
    repo_name=$(basename "$diff_file" .diff)
    if [[ -d "$repo_name" ]]; then
        echo "Applying diff to $repo_name"
        pushd "$repo_name" > /dev/null
        git apply "../$DIFF_DIR/$(basename "$diff_file")"
        popd > /dev/null
    else
        echo "Repository directory $repo_name not found, skipping."
    fi
done

