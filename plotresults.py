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

classes = []
configurations = []
colors = ["r", "g", "b", "y"] * 90
styles = ["-", "--", ":"] * 120

TIMEOUT=600
PENALTY=10

def printStats(header, cols):
    timecol = cols[header.index("Time")]
    statuscol = cols[header.index("Status")]
    configcol = cols[header.index("Configuration")]
    stats = {"ok": 0, "time": 0, "memory": 0, "fault": 0, "signal(9)": 0}
    par10 = 0
    for j, config in enumerate(configurations):
        par10 = 0
        total = 0
        stats["ok"] = stats["time"] = stats["memory"] = stats["fault"] = stats["signal(9)"] = 0
        for i, status in enumerate(statuscol):
            if configcol[i] == config:
                if status not in stats:
                    print("Invalid type of Status on line %d: %s" %(i+2, status))
                    sys.exit(1)
                stats[status] += 1
                total += 1
                if status == "ok":
                    par10 += float(timecol[i])
                else:
                    par10 += TIMEOUT*PENALTY
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

def cactusPlot(header, cols):
    timecol = cols[header.index("Time")]
    statuscol = cols[header.index("Status")]
    maxLenX = 0
    for k, Class in enumerate(classes):
        for j, Configuration in enumerate(configurations):
            col = [float(x) if statuscol[i] == "ok" else TIMEOUT for i,x in enumerate(timecol) if cols[-2][i] == Class and cols[-1][i] == Configuration]
            col.sort()
            X = range(1, len(col) + 1)
            if len(X) > maxLenX:
                maxLenX = len(X)
            label = Configuration
            if Class != "_ALL_":
                label = Class + "-" + Configuration
            mp.plot(X, col, colors[k] + styles[j], label=label)
    mp.legend(loc=0, borderaxespad=0.5)
    #bbox_to_anchor=(1, 1)
    mp.axis([0, maxLenX + 1, 0, 2000])
    mp.show()

def analyzeFamilies(header, cols):
    timecol = cols[header.index("Time")]
    statuscol = cols[header.index("Status")]
    family_data = []
    for k, Class in enumerate(classes):
        solved = [None] * len(configurations)
        for j, Configuration in enumerate(configurations):
            solved[j] = sum((1 for i in range(len(timecol)) if cols[-2][i] == Class and cols[-1][i] == Configuration and statuscol[i] == "ok"))
        mu = mean(solved)
        if mu == 0:
            print("No solver solved anything from the family '%s'" % Class)
        else:
            var = pvariance(solved, mu)
            std = pstdev(solved, mu)
            relstd = std / mu
            family_data.append([Class] + solved + [std, relstd])
    #family_data.sort(key=itemgetter(-1), reverse=True)
    family_data.sort(key=lambda x: x[-2] + x[-1], reverse=True)
    print()
    print("Families with the highest discrepancies:")
    print()
    for family in family_data[:20]:
        print(" ".join(map(str, family)))

def findOutliers(header, cols):
    timecol = cols[header.index("Time")]
    statuscol = cols[header.index("Status")]
    namecol = cols[header.index("Name")]
    instance_data = defaultdict(list)
    for j, Configuration in enumerate(configurations):
        for i,name in enumerate(namecol):
            if cols[-1][i] == Configuration:
                instance_data[name + "__" + cols[-2][i]].append(float(timecol[i]))
    outliers = []
    for instance, times in instance_data.items():
        mu = mean(times)
        if mu > 0:
            std = pstdev(times, mu)
            outliers.append((instance, std))
    outliers.sort(key=itemgetter(1), reverse=True)
    for x in outliers[:100]:
        print(("%s" + " %.02f" * len(instance_data[x[0]])) % (x[0], *instance_data[x[0]]))

def scatterPlot(header, cols):
    assert(len(configurations) == 2)
    timecol = cols[header.index("Time")]
    statuscol = cols[header.index("Status")]
    namecol = cols[header.index("Name")]
    data = [None, None]
    for j, Configuration in enumerate(configurations):
        data[j] = [(namecol[i], max(float(x), 0.00001)) if statuscol[i] == "ok" else (namecol[i], TIMEOUT) for i,x in enumerate(timecol) if cols[-1][i] == Configuration]
        data[j].sort(key=itemgetter(0))
        data[j] = [x[1] for x in data[j]]
    mp.scatter(*data)
    mp.plot([0,TIMEOUT*10], [0,TIMEOUT*10])
    l, u = min(min(data)) / 5, max(max(data)) * 5
    mp.xlim(l, u)
    mp.ylim(l, u)
    mp.gca().set_aspect('equal', adjustable='box')
    mp.gca().set_xscale("log")
    mp.gca().set_yscale("log")
    mp.xlabel(configurations[0])
    mp.ylabel(configurations[1])
    mp.show()

def readData(filename):
    global classes, configurations
    with open (filename, "r") as f:
        raw = f.readlines()
    table = [x.replace("\n", "").split(",") for x in raw]
    header = table[0]
    cols = list(zip(*(table[1:])))
    classes = list(set(cols[-2]))
    configurations = list(set(cols[-1]))
    classes.sort()
    configurations.sort()
    return header, cols

def getEasy(classes, configurations, instances, rundata, but=0, threshold=60):
    """
    Returns a list of instances that were solved by at least all but 'but' solvers in uder 'threshold' seconds.
    """
    easy = []
    for classname in classes:
        for instance in instances[classname]:
            if sum((ans != None and t <= threshold for (ans, t) in (rundata[getUID(config, classname, instance)] for config in configurations))) + but >= len(configurations):
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
    instances = defaultdict(list)
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

            classid = "__ALL__" if aggregate else classname
            classes.add(classid)
            configurations.add(config)

            if status == "time" and time < timeout:
                timeout = time
            
            instances[classid].append(instance)
            uid = getUID(config, classname, instance)
            if uid in rundata:
                print("Error on line %d: duplicate entry for config %s on instance %s of class %s" % (line_number, config, instance, classname))
                sys.exit(2)
            rundata[uid] = (answer, time)
    
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

    return success
    
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("filename", nargs='?', help="The csv file with the results as parsed by parseresults.py.")
    parser.add_argument("-c", "--cactus", action="store_true", default=False, help="Make a cactus plot of the various configurations and classes.")
    parser.add_argument("-g", "--aggregate", action="store_true", default=False, help="Treat all classes as one.")
    parser.add_argument("-f", "--families", action="store_true", default=False, help="Find families with large differences between solvers.")
    parser.add_argument("-o", "--outliers", action="store_true", default=False, help="Find instances with large differences between solvers.")
    parser.add_argument("-s", "--stats", action="store_true", default=False, help="Display statistics about the results.")
    parser.add_argument("-t", "--timeout", type=int, default=600, help="Specify the cutoff time that was used for these runs.")
    parser.add_argument("-x", "--scatter", action="store_true", default=False, help="Make a scatter plot that compares 2 configurations.")
    args = parser.parse_args()
    
    if args.filename == None:
        args.filename = "results_merged.csv"

    TIMEOUT = args.timeout
        
    header, cols = readData(args.filename)
    classes, configurations, instances, rundata, timeout = init(args.filename, args.aggregate)
    print("Guessed timeout: %d" % timeout)
    if verify(classes, configurations, instances, rundata):
        print("Solvers agree")
    threshold = 1
    print("Number of instances solved by all solvers in under %d seconds: %d" % (threshold, len(getEasy(classes, configurations, instances, rundata, threshold=threshold))))
    
    if args.stats:
        printStats(header, cols)
    else:
        import matplotlib.pyplot as mp
    
    if args.cactus:
        cactusPlot(header, cols)
    
    if args.scatter:
        scatterPlot(header, cols)

    if args.families:
        analyzeFamilies(header, cols)

    if args.outliers:
        findOutliers(header, cols)
