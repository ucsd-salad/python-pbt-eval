import csv

def add_commits():
    # Load commit hashes into a dict keyed by (owner, repo)
    commit_map = {}
    with open('corpus/repos_commits.csv', newline='') as commits_file:
        reader = csv.DictReader(commits_file)
        for row in reader:
            key = (row['owner'], row['repo'])
            commit_map[key] = row['commit']

    # Read hypothesis_uses_raw.csv and append /tree/<commit_hash> to each url
    with open('corpus/hypothesis_uses_raw.csv', newline='') as uses_file, \
        open('corpus/hypothesis_uses_with_commit.csv', 'w', newline='') as out_file:
        reader = csv.DictReader(uses_file)
        fieldnames = list(reader.fieldnames) + ['url_with_commit'] if reader.fieldnames is not None else ['url_with_commit']
        writer = csv.DictWriter(out_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            key = (row['user'], row['project_name'])
            commit = commit_map.get(key)
            if commit:
                row['url_with_commit'] = f"{row['url']}/tree/{commit}"
            else:
                row['url_with_commit'] = row['url']
            writer.writerow({'user': row['user'],'project_name': row['project_name'],'namespace': row['namespace'],'url': row['url_with_commit']})

if __name__ == "__main__":
    add_commits()
    print("Added commit hashes to hypothesis_uses_raw.csv and saved to hypothesis_uses_with_commit.csv")