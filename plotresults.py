#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  2 10:52:13 2017

@author: peitl
"""

import sys
import math
from argparse import ArgumentParser
from operator import itemgetter
from statistics import pvariance, pstdev, mean
from collections import defaultdict

colors = ["r", "g", "b", "y"] * 90
styles = ["-", "--", ":"] * 120

def printStats(classes, configurations, instances, rundata, timeout):
    stats = {"ok": 0, "time": 0, "memory": 0, "fault": 0, "signal(9)": 0}
    par10 = 0
    for j, config in enumerate(configurations):
        par10 = 0
        total = 0
        stats["ok"] = stats["time"] = stats["memory"] = stats["fault"] = stats["signal(9)"] = 0
        for classname in classes:
            for instance in instances[classname]:
                status = rundata[getUID(config, classname, instance)][2]
                if status not in stats:
                    print("Invalid type of Status on line %d: %s" %(i+2, status))
                    sys.exit(1)
                stats[status] += 1
                total += 1
                if status == "ok":
                    par10 += float(rundata[getUID(config, classname, instance)][1])
                else:
                    par10 += timeout*10
        print("####################" + "#" * 15 + "##")
        print("# Configuration:    %15s #" % config)
        print("####################" + "#" * 15 + "##")
        print("# Total instances:  %15d #" % total)
        print("# Instances solved: %15d #" % stats["ok"])
        print("# Timeouts:         %15d #" % stats["time"])
        print("# Memory outs:      %15d #" % stats["memory"])
        print("# Faults:           %15d #" % stats["fault"])
        print("# Signals:          %15d #" % stats["signal(9)"])
        print("#                   " + " " * 15 + " #")
        print("# PAR10:            %15d #" % (par10/total))
    print("####################" + "#" * 15 + "##")

def cactusPlot(classes, configurations, instances, rundata, timeout):
    maxLenX = 0
    for j, config in enumerate(configurations):
        for k, classname in enumerate(classes):
            times = sorted((rundata[getUID(config, classname, instance)][1] for instance in instances[classname]))
            X = range(1, len(times) + 1)
            if len(X) > maxLenX:
                maxLenX = len(X)
            label = config
            if classname != "_ALL_":
                label = classname + "-" + config
            mp.plot(X, times, colors[k] + styles[j], label=label)
    mp.legend(loc=0, borderaxespad=0.5)
    mp.axis([0, maxLenX + 1, 0, timeout + 1])
    mp.show()

def analyzeFamilies(classes, configurations, instances, rundata):
    family_data = []
    for classname in classes:
        solved = [0] * len(configurations)
        for instance in instances[classname]:
            for i, config in enumerate(configurations):
                if rundata[getUID(config, classname, instance)][0] != None:
                    solved[i] += 1
        mu = mean(solved)
        if mu == 0:
            print("No solver solved anything from the family '%s'" % classname)
        else:
            std = pstdev(solved, mu)
            relstd = std / mu
            family_data.append([classname] + solved + [std, relstd])
    family_data.sort(key=lambda x: x[-2] + x[-1], reverse=True)
    longest_name = max((len(family[0]) for family in family_data))
    format_string = "%{}s ".format(longest_name) + "%5d " * len(configurations) + "%7.2f %7.2f"
    print()
    print("Families with the highest discrepancies:")
    print()
    for family in family_data[:20]:
        print(format_string % tuple(family))

def findOutliers(classes, configurations, instances, rundata):
    outliers = []
    for classname in classes:
        for instance in instances[classname]:
            runtime_list = [rundata[getUID(config, classname, instance)][1] for config in configurations]
            outliers.append((instance, pstdev(runtime_list)))
    outliers.sort(key=itemgetter(1), reverse=True)
    for x in outliers[:20]:
        print(("%s" + " %.02f" * len(instance_data[x[0]])) % (x[0], *instance_data[x[0]]))

def scatterPlot(classes, configurations, instances, rundata):
    assert(len(configurations) == 2)
    instance_times = [[], []]
    for classname in classes:
        for instance in instances[classname]:
            for i, config in enumerate(configurations):
                instance_times[i].append(rundata[getUID(config, classname, instance)][1])
    mp.scatter(*instance_times)
    mp.plot([0,TIMEOUT*10], [0,TIMEOUT*10])
    l, u = min(min(instance_times)) / 5, max(max(instance_times)) * 5
    mp.xlim(l, u)
    mp.ylim(l, u)
    mp.gca().set_aspect('equal', adjustable='box')
    mp.gca().set_xscale("log")
    mp.gca().set_yscale("log")
    mp.xlabel(configurations[0])
    mp.ylabel(configurations[1])
    mp.show()

def getEasy(classes, configurations, instances, rundata, but=0, threshold=10):
    """
    Returns a list of instances that were solved by at least all but 'but' solvers in uder 'threshold' seconds.
    """
    easy = []
    for classname in classes:
        for instance in instances[classname]:
            if sum((ans != None and t <= threshold for (ans, t) in (rundata[getUID(config, classname, instance)] for config in configurations))) + but >= len(configurations):
                # create a regex pattern for grep filtering
                #easy.append(instance + ",.*," + classname + ",")
                easy.append(classname + "/" + instance)
    return easy

def getUID(config, classname, instance):
    return config + ":" + classname + "/" + instance

def init(filename, aggregate):
    """
    This function parses the data and creates the following data structures:

        # the list of benchmark classes, a.k.a. families
        classes = list(class:string)

        # the list of solvers/configurations
        configurations = list(config:string)

        # for every class a list of its instances
        instances = dict(class:string, list(instance:string))

        # for every instance and configuration identified as a tuple ('class/instance', 'config') the rundata
        rundata = dict{class/instance:string, config:string}{answer:enum(True, False, None), time:float)}

    It also guesses the timeout used as int(min(time)) over timed-out instances.
    If all instances are solved, the timeout is set to int(max(time)) + 1.
    """
    header = None
    name_idx = -1
    time_idx = -1
    ans_idx = -1
    ans_dict = {"10" : True, "20" : False}
    status_idx = -1
    class_idx = -1
    config_idx = -1

    classes = set()
    configurations = set()
    instances = defaultdict(set)
    rundata = {}
    timeout = math.inf

    with open(filename, "r") as f:
        header = {col : idx for idx, col in enumerate(next(f).rstrip('\n').split(","))}
        name_idx = header["Name"]
        time_idx = header["Time"]
        ans_idx = header["Result"]
        status_idx = header["Status"]
        class_idx = header["Class"]
        configuration_idx = header["Configuration"]

        line_number = 1
        for line in f:
            line_number += 1
            linedata = line.rstrip('\n').split(",")
            instance = linedata[name_idx]
            time = float(linedata[time_idx])
            answer = ans_dict.get(linedata[ans_idx])
            status = linedata[status_idx]
            classname = linedata[class_idx]
            config = linedata[config_idx]
            
            if aggregate:
                instance = classname + "/" + instance
                classname = "_ALL_"

            classes.add(classname)
            configurations.add(config)

            if status == "time" and time < timeout:
                timeout = time
            
            # for logscale
            time = max(time, 0.001)

            instances[classname].add(instance)
            uid = getUID(config, classname, instance)
            if uid in rundata:
                print("Error on line %d: duplicate entry for config %s on instance %s of class %s" % (line_number, config, instance, classname))
                sys.exit(2)
            rundata[uid] = (answer, time, status)
    
    timeout = int(timeout)
    classes = sorted(classes)
    configurations = sorted(configurations)

    return classes, configurations, instances, rundata, timeout

def verify(classes, configurations, instances, rundata):
    """
    This function checks the following properties:
        
        All answers provided for a single class/instance are the same

    """
    
    success = True

    for classname in classes:
        for instance in instances[classname]:
            votes = [[],[]]
            for config in configurations:
                ans = rundata[getUID(config, classname, instance)][0]
                if ans != None:
                    votes[ans].append(config)
            if len(votes[False]) * len(votes[True]) > 0:
                success = False
                print("Disagreement on instance '%s' of class '%s'" % (instance, classname))
                print("The following solvers/configs say False: " + ", ".join(votes[False]))
                print("The following solvers/configs say True:  " + ", ".join(votes[True]))

    if len(rundata) != len(configurations) * sum((len(instances[classname]) for classname in classes)):
        success = False
        print("Error: the number of run-data entries should be number of instances times the number of configurations.")
    return success

def venn(classes, configurations, instances, rundata):
    """
    This function calculates the values in a Venn diagram of
    solved instances by configurations
    """
    values = [0] * 2 ** len(configurations)
    for classname in classes:
        for instance in instances[classname]:
            subset_idx = 0
            for i, config in enumerate(configurations):
                ans = rundata[getUID(config, classname, instance)][0]
                if ans != None:
                    subset_idx += 2 ** i
            values[subset_idx] += 1
    for idx, val in enumerate(values):
        i = 0
        while idx > 0:
            if idx % 2 == 1:
                print(configurations[i] + " ", end="")
            idx //= 2
            i += 1
        print(val)

    
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("filename", nargs='?', help="The csv file with the results as parsed by parseresults.py.")
    parser.add_argument("-c", "--cactus", action="store_true", default=False, help="Make a cactus plot of the various configurations and classes.")
    parser.add_argument("-e", "--easy", type=int, default=0, help="Identify instances solved by all solvers within the given time limit.")
    parser.add_argument("-g", "--aggregate", action="store_true", default=False, help="Treat all classes as one.")
    parser.add_argument("-f", "--families", action="store_true", default=False, help="Find families with large differences between solvers.")
    parser.add_argument("-o", "--outliers", action="store_true", default=False, help="Find instances with large differences between solvers.")
    parser.add_argument("-s", "--stats", action="store_true", default=False, help="Display statistics about the results.")
    parser.add_argument("-t", "--timeout", type=int, default=0, help="Specify the cutoff time that was used for these runs.")
    parser.add_argument("-v", "--venn", action="store_true", default=False, help="Compute the Venn diagram of solved instances for the configurations.")
    parser.add_argument("-x", "--scatter", action="store_true", default=False, help="Make a scatter plot that compares 2 configurations.")
    args = parser.parse_args()
    
    if args.filename == None:
        args.filename = "results_merged.csv"
        
    classes, configurations, instances, rundata, timeout = init(args.filename, args.aggregate)
    if args.timeout > 0:
        timeout = args.timeout
    else:
        print("Guessed timeout: %d" % timeout)
    if verify(classes, configurations, instances, rundata):
        print("Solvers agree ✓")
    
    if args.stats:
        printStats(classes, configurations, instances, rundata, timeout)
    elif args.families:
        analyzeFamilies(classes, configurations, instances, rundata)
    elif args.outliers:
        findOutliers(classes, coonfigurations, instances, rundata)
    elif args.venn:
        venn(classes, configurations, instances, rundata)
    elif args.easy > 0:
        easy_instances = getEasy(classes, configurations, instances, rundata, threshold=args.easy)
        print("\n".join(easy_instances))
    else:
        import matplotlib.pyplot as mp
        if args.cactus:
            cactusPlot(classes, configurations, instances, rundata, timeout)
        elif args.scatter:
            scatterPlot(classes, configurations, instances, rundata)

