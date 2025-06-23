import pandas as pd 

def convert_to_csv(fname):
    def get_data(ln):
        info = ln.split("=")[1].split()
        proj_name = info[2]
        # skip ones found in Hypothesis's repo
        if "HypothesisWorks" in proj_name:
            return None
        [user, pname] = proj_name.split("/")
        info_dict = {"user": user, "project_name": pname, "namespace": info[4], "url": info[6]}
        return info_dict

    with open(fname) as f:
        f.readline() # skip first line
        proj_info = [data for data in (get_data(ln) for ln in f) if data is not None]
        df = pd.DataFrame(proj_info)
        df = df.sort_values(by = "user")
        df.to_csv("hypothesis_imports_raw.csv")
    return

def main():
    boa_file = "boa-job107852-output.txt"
    convert_to_csv(boa_file)

if __name__ == "__main__":
    main()