#!/usr/bin/python
import sys, os.path, os, urllib, json
import model
from urllib.request import urlopen
from urllib.parse import urlencode

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

def read_todoist_resources(token):
    """Read user resources from https://todoist.com/API/v7/sync using the specified API token.
    See https://developer.todoist.com/#read-resources

    token should be a string representation of the users API token, e.g. '0123456789abcdef0123456789abcdef01234567'"""
    resource_types = '["items", "notes", "projects", "user"]'
    url = "https://todoist.com/API/v7/sync"
    data = urlencode({
        "token": token,
        "sync_token": "*",
        "resource_types": resource_types,
    })
    fd = urlopen(url, data.encode('utf-8'))
    content = fd.read()
    fd.close()
    return json.loads(content.decode('utf-8'))

def print_usage(error=None):
    usage = """Usage: Todoist-API-key output-file [options]
        Todoist-API-key: 40 character API token found under Todoist account settings
        output-file/output-folder: a valid file path in the local file system
        -a, --append-output
            Instead of overwriting the output file, append Org output to the end of it."""
    if isinstance(error, str):
        print("%s" % error)
    print(usage)


def touch_file(filepath): open(filepath, 'a').close()

def write_to_file(filepath, output_lines, append=False):
    if append:
        f = open(filepath, 'a')
    else:
        f = open(filepath, 'w')
    # Write to the output file and close it
    for line in output_lines:
        f.write("%s\n" % line)
    f.close()

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=False)

    # Exclude the path of this file from the argument list
    args = sys.argv[1:]

    # There must be 2-3 arguments
    if not 2 <= len(args) <= 3:
        print_usage("Error: wrong number of arguments")
        exit()

    user_resources = {"projects": [], "items": [], "notes": [], "users": []}
    api_token = args[0]

    # Use the API token to get the user resources
    try:
        user_resources = merge_two_dicts(user_resources, read_todoist_resources(api_token))
    except urllib.error.HTTPError as e:
        print_usage("HTTPError: something is probably wrong with your API token")
        exit()

    # If the output path doesn't exist then create it as a file
    if not os.path.exists(args[1]):
        try:
            touch_file(args[1])
        except OSError as e:
            print_usage(e.message)
            exit()

    # Account for options
    if len(args) == 3 and (args[2] == "-a" or args[2] == "--append-output"):
        append = True
    else:
        append = False

    # Process the user resources
    projects, my_timezone = model.process_todoist_resources(user_resources)

    # One file for all projects
    if os.path.isfile(args[1]):
        output_lines = model.process_todoist_projects(projects, my_timezone)
        write_to_file(args[1], output_lines, append)
        print("Successfully created and populated '%s'!" % os.path.basename(args[1]))

    # One file for each project
    elif os.path.isdir(args[1]):
        for project in projects:
            output_lines = model.process_todoist_project(project, my_timezone, initial_heading_level=0)

            # Construct a file path for the project file
            output_filepath = os.path.join(args[1], project["name"] + ".org")

            # Make sure the file exists
            touch_file(output_filepath)

            write_to_file(output_filepath, output_lines, append)
            print("Successfully created and populated '%s'!" % os.path.basename(output_filepath))

    else:
        print_usage("Error: output file path is neither a file or a directory!")
        exit()
