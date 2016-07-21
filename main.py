#!/usr/bin/python
import csv, sys, os.path, os
from fnmatch import fnmatch
import model

# Adapted from:  http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression?rq=1
def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy.
    If either x or y are None, return whichever dict of x and y is not None,
    otherwise return the empty dictionary {}."""
    if x is None and y is None:
        return {}
    elif x is None:
        return y
    elif y is None:
        return x
    z = x.copy()
    z.update(y)
    return z

def collect_csv_files(dirpath):
    assert os.path.isdir(dirpath)
    root = dirpath
    pattern = "*.csv"

    csv_files = []
    # Adapted from: http://stackoverflow.com/questions/2909975/python-list-directory-subdirectory-and-files?rq=1
    for path, subdirs, files in os.walk(root):
        for name in files:
            if fnmatch(name, pattern):
                csv_files.append(os.path.join(path, name))
    return csv_files

def process_csv(filepath):
    """Take a file path to a .csv file and return a dictionary mapping the file name to a list of processed CSV rows.
    """
    with open(filepath) as csvfile:
        reader = csv.reader(csvfile)
        filename = os.path.basename(filepath)
        return {filename: [row for row in reader]}

def print_usage(error=None):
    usage = """Usage: <input-directory / .csv file> <output-file> [options]
    If used, input directory should contain at least one .csv file
    Options
        -a, --append-output
            Instead of overwriting the output file, append Org output to the end of it."""
    print(usage)
    if isinstance(error, str):
        print("%s" % error)

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=False)

    # Exclude the path of this file from the argument list
    args = sys.argv[1:]

    # There must be 2 arguments
    if not 2 <= len(args) <= 3:
        print_usage("Error: wrong number of arguments")
        exit()

    project_dict = {}

    # If the file path given as the first argument is a file, then had that file
    # to the processing list
    if os.path.isfile(args[0]):
        project_dict = process_csv(csv_file)

    # Otherwise if the file path given is a directory, then collect all .CSV
    # files in that directory and add them to the processing list
    elif os.path.isdir(args[0]):
        csv_files = collect_csv_files(args[0])
        for csv_file in csv_files:
            project_dict = merge_two_dicts(process_csv(csv_file), project_dict)
        if len(csv_files) == 0:
            print_usage("Error: input directory must contain at least one .csv file!")
            exit()

    else:
        print_usage("Error: input file path must exist!")
        exit()

    # If the output path doesn't exist then create it as a file
    if not os.path.exists(args[1]):
        open(args[1], 'a').close()

    if os.path.isdir(args[1]):
        print_usage("Error: output file path must be a file!")
        exit()

    # Process project_dict using the model module
    output_lines = model.process_todoist_projects(project_dict)

    # Account for options
    if len(args) == 3 and (args[2] == "-a" or args[2] == "--append-output"):
        f = open(args[1], 'a')
    else:
        f = open(args[1], 'w')

    # Write to the output file and close it
    for line in output_lines:
        f.write("%s\n" % line)
    f.close()
    print("Successfully created and populated '%s'!" % os.path.basename(args[1]))
