#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, os, sys
import multiprocessing

patterns = [r"[^\s/]*$", r"([^\s]*) [^\s]*$", r"([^\s]*) [^\s]*$", r"[^\s]*$", r"[^\s]*$"]
regex = [re.compile(pattern) for pattern in patterns]
group = [0, 1, 1, 0, 0]
header = ["Name", "Time", "Space", "Result", "Status", "LC", "LT", "FDA", "BT", "BTDL", "TD", "LD", "FLD", "DCR", "PI", "LR", "TRD", "TRR", "DEPQBFFDA", "DEPQBFBT", "Class", "Configuration"]
log_identifiers = [None, "time:", "space:", "result:", "status:"]
out_identifiers = ["Number of learned clauses:",
                   "Number of learned terms:",
                   "Fraction of decisions among assignments:",
                   "Number of backtracks:",
                   "Number of backtracks caused by dependency learning:",
                   "Number of trivial dependencies:",
                   "Number of learned dependencies:", 
                   "Learned dependencies as a fraction of trivial:",
                   "Number of dependency conflicts resolved by RRS:",
                   "Number of proven independencies:",
                   "Number of literals reduced thanks to RRS:",
                   "Amount of time spent computing RRS deps (s):",
                   "Amount of time spent on generalized forall reduction (s):"]
                   

err_identifiers = ["dec. per assignm.:",
                   "backtracks:"]                


def getValuesFromLogAndOutFile(filename):
    """
    Parses the Instance name, Running time, Space and Result
    from a log file.
    
    Additionally also parses other stats from the corresponding .out and .err files.
    This can be used to collect values output by --print-stats.
    """
    
    global regex, group, log_identifiers
    values = ["Name", "Time", "Space", "Result", "Status"] + ["NA"] * (len(out_identifiers) + len(err_identifiers))
    values[0] = filename[filename.rfind("/")+1:-4]
    
    with open(filename) as f:
        for s in f:
            if "sample:" in s:
                continue
            for i in range(1, len(log_identifiers)):
                if log_identifiers[i] in s:
                    match = regex[i].search(s)
                    if match:
                        values[i] = match.group(group[i])
                    break
    
    if values[4] == "ok" and values[3] not in ["10","20"]:
        values[4] = "time"

    filename = filename[:-3] + "out"
    if os.path.isfile(filename):
        with open(filename) as f:
            for s in f:
                for i,v in enumerate(out_identifiers):
                    if s.startswith(v):
                        values[len(log_identifiers)+i] = s[len(v):].strip()
                        break
    
    filename = filename[:-3] + "err"
    if os.path.isfile(filename):
        with open(filename) as f:
            for s in f:
                for i,v in enumerate(err_identifiers):
                    if s.startswith(v):
                        values[len(log_identifiers)+len(out_identifiers)+i] = s[len(v):].strip()
                        break
    return values

root_filter_pattern = r"[^/]*$"
root_filter_regex = re.compile(root_filter_pattern)

def walkResults(in_dir="results", out_file="results_processed.csv", remainder=0, modulus=1):
    """
    The experiment setup assumes we will run different configurations (solvers)
    on benchmark sets divided into classes.

    The results should be stored as follows. They are all in the directory 'in_dir',
    with the name of the directory encoding the current configuration being run
    either as the string following '_' if '_' is present in the name, or the last three
    letters otherwise.

    The directory 'in'dir' can contain subdirectories corresponding to classes. The class
    of a given instances is the name of its immediate containing directory. In case the
    benchmark set does not have classes, simply put all instances directly to 'in_dir'
    and the classname '_ALL_' will be assigned to all instances.
    """
    configuration = in_dir[-3:]
    idx = in_dir.rfind("_")
    if idx != -1:
        configuration = in_dir[idx+1:]
    
    result_table = []
    i = 0
    for root, dirs, files in os.walk(in_dir):
        dirs[:] = [d for d in dirs if d[0] != "."]
        classname = root_filter_regex.search(root).group(0)
        if classname == in_dir:
            # This means that instances are not further distributed into classes.
            # Because of that, let all instancess have the same class '_ALL_'.
            classname = "_ALL_"
        for f in files:
            if f.endswith(".log"):
                if i % modulus == remainder:
                    result_table.append(getValuesFromLogAndOutFile(os.path.join(root, f)))
                    result_table[-1].append(classname)
                    result_table[-1].append(configuration)
                i += 1
    return result_table

def writeCSV(out_file, result_table):
    with open(out_file, "w") as f:
        print(",".join(header), file=f)
        for entry in result_table:
            print(*entry, sep=",", file=f)
    return None
            
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("USAGE: parseresults.py <in_dir> <out_file>")
        sys.exit(1)
    in_dir = sys.argv[1]
    out_file = sys.argv[2]
    num_proc = multiprocessing.cpu_count()
    def f(x):
        return walkResults(in_dir, out_file, remainder=x, modulus=num_proc)
    with multiprocessing.Pool(num_proc) as p:
        result_table = [elem for table in p.map(f, range(num_proc)) for elem in table]
        writeCSV(out_file, result_table)
