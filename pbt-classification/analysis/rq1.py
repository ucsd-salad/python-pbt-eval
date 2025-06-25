import pandas as pd

def ans_rq1_corpus(detections_file="data/artifact_eval/detections_0-1587.csv"):
    detections = pd.read_csv(detections_file)
    detection_cols = ['roundtrip', 'partial_roundtrip', 'hetero_gv_roundtrip',  'commutative', 'partial_commutative', 'const_eq', 'const_inclusion', 'inclusion', 'typecheck', 'const_bounds', 'gen_val_bounds', 'cross_gv_bounds', 'exception', 'const_neq', 'gen_val_neq']
    sum_of_true = detections[detection_cols].sum(axis=1)
    unclassified = detections[sum_of_true == 0]
    percent_unclassified = len(unclassified)/len(detections) * 100
    print(f"Percent of tests classified: {100 - percent_unclassified:.2f}%")
    num_asserts = len(detections['assert_stmt'])
    num_rt = detections.sum(0)['roundtrip']
    num_prt = detections.sum(0)['partial_roundtrip']
    num_comm = detections.sum(0)['commutative']
    num_pcomm = detections.sum(0)['partial_commutative']
    num_const_eq = detections.sum(0)['const_eq']
    num_const_incl = detections.sum(0)['const_inclusion']
    num_incl = detections.sum(0)['inclusion']
    num_tc = detections.sum(0)['typecheck']
    num_const_bounds = detections.sum(0)['const_bounds']
    num_gv_bounds = detections.sum(0)['gen_val_bounds']
    num_cgv_bounds = detections.sum(0)['cross_gv_bounds']
    num_exception = detections.sum(0)['exception']
    num_const_neq = detections.sum(0)['const_neq']
    num_gv_neq = detections.sum(0)['gen_val_neq']
    percent_rt = (num_rt)/(num_asserts) * 100
    percent_prt = (num_prt)/(num_asserts) * 100
    percent_comm = (num_comm)/(num_asserts) * 100
    percent_pcomm = (num_pcomm)/(num_asserts) * 100
    percent_const_eq = (num_const_eq)/(num_asserts) * 100
    percent_const_incl = (num_const_incl)/(num_asserts) * 100
    percent_incl = (num_incl)/(num_asserts) * 100
    percent_tc = (num_tc)/(num_asserts) * 100
    percent_const_bounds = (num_const_bounds)/(num_asserts) * 100
    percent_gv_bounds = (num_gv_bounds)/(num_asserts) * 100
    percent_exception = (num_exception)/(num_asserts) * 100
    percent_const_neq = (num_const_neq)/(num_asserts) * 100
    percent_gv_neq = (num_gv_neq)/(num_asserts) * 100
    print("percent roundtrip: ", percent_rt)
    print("percent prt:", percent_prt)
    print("percent comm: ", percent_comm + percent_pcomm)
    print("percent const eq: ", percent_const_eq)
    print("percent const inclusion: ", percent_const_incl)
    print("percent inclusion: ", percent_incl)
    print("percent typecheck: ", percent_tc)
    print("percent const bounds: ", percent_const_bounds)
    print("percent gv bounds: ", percent_gv_bounds)
    print("percent exception: ", percent_exception)
    print("percent const neq: ", percent_const_neq)
    print("percent gv neq: ", percent_gv_neq)


def ans_rq1_testset(testset_detections="data/artifact_eval/detections_new_examples_0-50.csv"):
    detections = pd.read_csv(testset_detections)
    detection_cols = ['roundtrip', 'partial_roundtrip', 'hetero_gv_roundtrip',  'commutative', 'partial_commutative', 'const_eq', 'const_inclusion', 'inclusion', 'typecheck', 'const_bounds', 'gen_val_bounds', 'cross_gv_bounds', 'exception', 'const_neq', 'gen_val_neq']
    sum_of_true = detections[detection_cols].sum(axis=1)
    unclassified = detections[sum_of_true == 0]
    percent_unclassified = len(unclassified)/len(detections) * 100
    print(f"Percent of tests classified: {100 - percent_unclassified:.2f}%")
    num_asserts = len(detections['assert_stmt'])
    num_rt = detections.sum(0)['roundtrip']
    num_prt = detections.sum(0)['partial_roundtrip']
    num_comm = detections.sum(0)['commutative']
    num_pcomm = detections.sum(0)['partial_commutative']
    num_const_eq = detections.sum(0)['const_eq']
    num_const_incl = detections.sum(0)['const_inclusion']
    num_incl = detections.sum(0)['inclusion']
    num_tc = detections.sum(0)['typecheck']
    num_const_bounds = detections.sum(0)['const_bounds']
    num_gv_bounds = detections.sum(0)['gen_val_bounds']
    num_cgv_bounds = detections.sum(0)['cross_gv_bounds']
    num_exception = detections.sum(0)['exception']
    num_const_neq = detections.sum(0)['const_neq']
    num_gv_neq = detections.sum(0)['gen_val_neq']
    percent_rt = (num_rt)/(num_asserts) * 100
    percent_prt = (num_prt)/(num_asserts) * 100
    percent_comm = (num_comm)/(num_asserts) * 100
    percent_pcomm = (num_pcomm)/(num_asserts) * 100
    percent_const_eq = (num_const_eq)/(num_asserts) * 100
    percent_const_incl = (num_const_incl)/(num_asserts) * 100
    percent_incl = (num_incl)/(num_asserts) * 100
    percent_tc = (num_tc)/(num_asserts) * 100
    percent_const_bounds = (num_const_bounds)/(num_asserts) * 100
    percent_gv_bounds = (num_gv_bounds)/(num_asserts) * 100
    percent_exception = (num_exception)/(num_asserts) * 100
    percent_const_neq = (num_const_neq)/(num_asserts) * 100
    percent_gv_neq = (num_gv_neq)/(num_asserts) * 100
    print("percent roundtrip: ", percent_rt)
    print("percent prt:", percent_prt)
    print("percent comm: ", percent_comm + percent_pcomm)
    print("percent const eq: ", percent_const_eq)
    print("percent const inclusion: ", percent_const_incl)
    print("percent inclusion: ", percent_incl)
    print("percent typecheck: ", percent_tc)
    print("percent const bounds: ", percent_const_bounds)
    print("percent gv bounds: ", percent_gv_bounds)
    print("percent exception: ", percent_exception)
    print("percent const neq: ", percent_const_neq)
    print("percent gv neq: ", percent_gv_neq)

if __name__ == "__main__":
    print("Corpus \n")
    ans_rq1_corpus()
    print("\n\n\nTest Set \n")
    ans_rq1_testset()