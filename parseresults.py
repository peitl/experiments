#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spyder Editor

@author: tp
"""

import re, os, sys

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
    basename = filename[filename.rfind("/")+1:-4]
    values[0] = basename
    
    with open(filename) as f:
        for s in f:
            for i,v in enumerate(log_identifiers):
                if i > 0 and v in s:
                    match = regex[i].search(s)
                    if match:
                        values[i] = match.group(group[i])
                    break
    
    if values[4] == "ok" and values[3] not in ["10","20"]:
        values[4] = "time"
    filename = list(filename)
    filename[-3:] = ['o', 'u', 't']
    filename = "".join(filename)
    if os.path.isfile(filename):
        with open(filename) as f:
            for s in f:
                for i,v in enumerate(out_identifiers):
                    if s.startswith(v):
                        values[len(log_identifiers)+i] = s[len(v):].strip()
                        break
    
    filename = list(filename)
    filename[-3:] = ['e', 'r', 'r']
    filename = "".join(filename)
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

def walkResults(in_dir="results", out_file="results_processed.csv"):
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
    for root, dirs, files in os.walk(in_dir):
        dirs[:] = [d for d in dirs if d[0] != "."]
        classname = root_filter_regex.search(root).group(0)
        if classname == in_dir:
            # This means that instances are not further distributed into classes.
            # Because of that, let all instancess have the same class '_ALL_'.
            classname = "_ALL_"
        for f in files:
            if f.endswith(".log"):
                result_table.append(getValuesFromLogAndOutFile(os.path.join(root, f)))
                result_table[-1].append(classname)
                result_table[-1].append(configuration)

    # sort results by time, ascending
    #
    # EDIT: no sorting anymore, because unsorted results may also be useful.
    # Either uncomment and parse that way to sort, or sort in R directly.
    #
    #result_table.sort(key=lambda entry: (float(entry[1]), float(entry[2])))
    with open(out_file, "w") as f:
        print(",".join(header), file=f)
        for entry in result_table:
            print(*entry, sep=",", file=f)
    return None
            
if __name__ == '__main__':
    walkResults(sys.argv[1], sys.argv[2])
