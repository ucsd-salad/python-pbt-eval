import json
import csv

def main():
    example_list = []
    with open('corpus/github_output.txt', 'r') as file:
        example_list = json.load(file)

    # print(example_list[0])
    relevant_examples = []
    urls = {}
    for ex in example_list:
        if ex['textMatches'][0]["matches"][0]["text"] == "import hypothesis":
            exstr = ",".join(ex['repository']['nameWithOwner'].split("/")) + "," + ex['path']
            relevant_examples.append(exstr)
            urls[exstr] = ex["url"]
    print(len(relevant_examples))
    uses = []
    with open("corpus/hypothesis_uses_with_commit.csv") as f:
        reader = csv.reader(f)
        for i, values in enumerate(reader):
            if i == 0:
                continue
            else:
                uses.append(",".join(values[:3]))
    actual_examples = []
    for ex in relevant_examples:
        if ex not in uses:
            actual_examples.append(ex)
    with open("corpus/cleaned_new_examples.csv", 'w') as f:
        csvw = csv.writer(f)
        csvw.writerows([d.split(",") + [urls[d]] for d in actual_examples])

if __name__ == "__main__":
    main()