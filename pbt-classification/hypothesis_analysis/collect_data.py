import csv
import os
import sys
import json
from typing import List, Dict
import pickle
from hypothesis_analysis.detector_utils import DetectionException
from hypothesis_analysis.pbt_detectors import detect_pbts, FIELDNAMES
import time

HEADER = ["user", "project_name", "namespace", "function", "assert_stmt"] + FIELDNAMES


def create_pickle(
    input_filename: str = "corpus/hypothesis_uses_with_commit.csv",
    output_filename: str = "corpus/hypothesis_uses_with_commit.pkl",
):
    with open(input_filename) as f:
        uses: List[List] = []
        reader = csv.reader(f)
        for i, values in enumerate(reader):
            if i == 0:
                continue
            else:
                uses.append(values[:3])
                # uses.append(values)

    with open(output_filename, "wb") as f:
        pickle.dump(uses, f)
    return


def get_pickle(pickle_file: str) -> List[List]:
    with open(pickle_file, "rb") as f:
        uses = pickle.load(f)
        return uses


def process_data(start, end, pickle_filename="corpus/hypothesis_uses.pkl",
                 failed_detections_filename="data/artifact_eval/failed_detections", 
                 detections_filename="data/artifact_eval/detections"):
    uses = get_pickle(pickle_filename)  # length: 1586
    failed_detections: List[List[str]] = []
    detections: List[Dict[str, str]] = []

    section = (start, end)

    # index 0: user, index 1: project name, index 2: namespace (filename), index 3: url
    for j, use in enumerate(uses[section[0] : section[1]]):
        try:
            print(f"{start + j}: {use[0]} | {use[1]} | {use[2]}")
            detections_info = detect_pbts(use[0], use[1], use[2])
            for i in range(len(detections_info)):
                detections += detections_info[i]
        except DetectionException as ex:
            print(ex)
            failed_detections.append(use + [f"failed detection {j}", str(ex)])
            time.sleep(2)
            continue
        except Exception as ex:
            print(ex)
            failed_detections.append(use + [f"failed setup {j}", str(ex)])
            time.sleep(2)
            continue

    if failed_detections != []:
        with open(f"{failed_detections_filename}_{section[0]}-{section[1]}.txt", "w") as f:
            json.dump(failed_detections, f, indent=4)
    with open(f"{detections_filename}_{section[0]}-{section[1]}.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        for detection in detections:
            writer.writerow(detection)
    print("number of detections: ", len(detections))
    return

def main():
    if os.path.exists("corpus/hypothesis_uses_with_commit.pkl"):
        print("Using existing pickle file.")
    else:
        print("Creating pickle file from corpus/hypothesis_uses_with_commit.csv")
    create_pickle("corpus/cleaned_new_examples.csv", "corpus/cleaned_new_examples.pkl")
    # if len(sys.argv) == 1:
    #     start = 0
    #     end = 1587
    # else:
    #     start = int(sys.argv[1])
    #     end = int(sys.argv[2])
    # process_data(start, end)
    process_data(0, 50, pickle_filename="corpus/cleaned_new_examples.pkl", failed_detections_filename="data/artifact_eval/failed_new_examples", detections_filename="data/artifact_eval/detections_new_examples")


if __name__ == "__main__":
    main()
