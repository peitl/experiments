#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, os, sys
import multiprocessing
from argparse import ArgumentParser
from operator import itemgetter

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


def getValuesFromLogAndOutFile(filename, general=False):
    """
    Parses the Instance name, Running time, Space and Result
    from a log file.
    
    Additionally also parses other stats from the corresponding .out and .err files.
    This can be used to collect values output by --print-stats.
    """
    
    global regex, group, log_identifiers
    log_values = ["Name", "Time", "Space", "Result", "Status"]
    log_values[0] = filename[filename.rfind("/")+1:-4]
    
    with open(filename) as f:
        for s in f:
            if "sample:" in s:
                continue
            for i in range(1, len(log_identifiers)):
                if log_identifiers[i] in s:
                    match = regex[i].search(s)
                    if match:
                        log_values[i] = match.group(group[i])
                    break
    
    if log_values[4] == "ok" and log_values[3] not in ["10","20"]:
        log_values[4] = "time"

    if general:
        return log_values

    out_values = ["NA"] * len(out_identifiers)
    filename = filename[:-3] + "out"
    if os.path.isfile(filename):
        with open(filename) as f:
            for s in f:
                for i,v in enumerate(out_identifiers):
                    if s.startswith(v):
                        out_values[i] = s[len(v):].strip()
                        break
    
    err_values = ["NA"] * len(err_identifiers)
    filename = filename[:-3] + "err"
    if os.path.isfile(filename):
        with open(filename) as f:
            for s in f:
                for i,v in enumerate(err_identifiers):
                    if s.startswith(v):
                        err_values[i] = s[len(v):].strip()
                        break

    return log_values + out_values + err_values

root_filter_pattern = r"[^/]*$"
root_filter_regex = re.compile(root_filter_pattern)

def getFileList(in_dir="results"):
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

    file_list = []
    for root, dirs, files in os.walk(in_dir):
        dirs[:] = [d for d in dirs if d[0] != "."]
        classname = root_filter_regex.search(root).group(0)
        if classname == in_dir:
            # This means that instances are not further distributed into classes.
            # Because of that, let all instancess have the same class '_ALL_'.
            classname = "_ALL_"
        for f in files:
            if f.endswith(".log"):
                file_list.append((root, classname, f))
    return file_list

def getResultsFromFileList(file_list):
    config = in_dir[-3:]
    idx = in_dir.rfind("_")
    if idx != -1:
        config = in_dir[idx+1:]
    
    result_table = [getValuesFromLogAndOutFile(os.path.join(root, logfile)) + [classname, config] for root, classname, logfile in file_list]
    return result_table

def writeCSV(out_file, result_table):
    with open(out_file, "w") as f:
        print(",".join(header), file=f)
        for entry in result_table:
            print(*entry, sep=",", file=f)
    return None

def parseDirName(results_dir):
    results_dir = results_dir.rstrip("/")
    results_dir = results_dir[results_dir.rfind("/") + 1:]
    if results_dir.startswith("results_"):
        results_dir = results_dir[8:]

    idx = results_dir.rfind("_")
    if idx == -1:
        return results_dir + ".csv"
    else:
        return results_dir[idx+1:] + "_" + results_dir[:idx] + ".csv"
            
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("results_dir", help="Directory containing (possibly in deeper subdirectories) all .log, .out, and .err files.")
    parser.add_argument("-o", "--outfile", type=str, default=None, help="Specify output file. The default is to guess <inst_set> and <config> and write to <config>_<inst_set>.csv.")
    parser.add_argument("-g", "--general", action="store_true", default=False, help="Do not parse auxiliary information from .out and .log files.")
    args = parser.parse_args()

    in_dir = args.results_dir
    out_file = args.outfile
    if out_file == None:
        out_file = parseDirName(args.results_dir)

    file_list = getFileList(in_dir)
    writeCSV(out_file, sorted(getResultsFromFileList(file_list), key=itemgetter(0)))

    #num_proc = multiprocessing.cpu_count()
    #sliced_file_lists = [file_list[r::num_proc] for r in range(num_proc)]

    #with multiprocessing.Pool(num_proc) as p:
    #    writeCSV(out_file, [elem for table in p.map(getResultsFromFileList, sliced_file_lists) for elem in table])
