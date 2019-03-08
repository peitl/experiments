#!/usr/bin/env python3

import sys

def read_easy(filename):
    easy_instances = set()
    with open(filename) as f:
        for line in f:
            classname, instance = line.strip().split("/")
            easy_instances.add((classname, instance))
    return easy_instances

def read_and_filter(filename, easy_set):
    filtered_results = []
    with open(filename) as f:
        header = next(f)
        filtered_results.append(header)
        for line in f:
            cells = line.strip().split(",")
            classname = cells[-2]
            instance = cells[0]
            if (classname, instance) not in easy_set:
                filtered_results.append(line)
    return filtered_results
                
if __name__ == "__main__":
    easy_file = sys.argv[1]
    easy_instances = read_easy(easy_file)
    print(len(easy_instances))

    for i in range(2, len(sys.argv)):
        filtered_results = read_and_filter(sys.argv[i], easy_instances)
        with open(sys.argv[i], "w") as f:
            print("".join(filtered_results), file=f, end="")
