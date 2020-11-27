#!/usr/bin/python
import argparse
import json
import logging
import os
from urllib.request import urlopen
from urllib.parse import urlencode

import model


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
    with urlopen(url, data.encode('utf-8')) as fd:
        content = fd.read()

    return json.loads(content.decode('utf-8'))


def touch_file(filepath):
    open(filepath, 'a').close()


def write_to_file(filepath, output_lines, append=False):
    mode = 'a' if append else 'w'
    with open(filepath, mode) as f:
        for line in output_lines:
            f.write("%s\n" % line)


def _valid_api_token(string):  # argparse helper function
    if len(string) != 40:
        msg = "%r is not a valid API token" % string
        raise argparse.ArgumentTypeError(msg)
    return string


def main():
    # Define command-line arguments.
    parser = argparse.ArgumentParser(
        description="Transform Todoist projects into Emacs Org mode files"
    )
    parser.add_argument(
        "api_token", type=_valid_api_token,
        help="40 character Todoist API token found under Settings->Integrations."
    )
    parser.add_argument(
        "dest", help="File or directory path."
    )
    parser.add_argument(
        "-a", "--append-output", default=False, action="store_true",
        help="Append Org output to the end of an output file instead of "
             "overwriting it. This does nothing if outputting multiple files to a "
             "directory."
    )

    # Parse command-line arguments from sys.argv.
    args = parser.parse_args()

    # Set up logging.
    logging.basicConfig(format="%(levelname)s: %(message)s")
    log = logging.getLogger()

    # Use the API token to get the user resources.
    try:
        user_resources = read_todoist_resources(args.api_token)
    except Exception as err:
        log.error("Could not retrieve data from Todoist: %s", err)
        exit(1)

    # If the output path doesn't exist then create it as a file.
    if not os.path.exists(args.dest):
        try:
            touch_file(args.dest)
        except OSError as err:
            log.error("Could not write to output file: %s", err)
            exit(2)

    # Process the user resources
    projects, my_timezone = model.process_todoist_resources(user_resources)

    # One file for all projects
    if os.path.isfile(args.dest):
        output_lines = model.process_todoist_projects(projects, my_timezone)
        write_to_file(args.dest, output_lines, args.append_output)
        print("Successfully created and populated '%s'!" % os.path.basename(args.dest))

    # One file for each project
    elif os.path.isdir(args.dest):
        for project in projects:
            output_lines = model.process_todoist_project(project, my_timezone, initial_heading_level=0)

            # Construct a file path for the project file
            output_filepath = os.path.join(args.dest, project["name"] + ".org")

            # Make sure the file exists
            touch_file(output_filepath)

            write_to_file(output_filepath, output_lines, args.append_output)
            print("Successfully created and populated '%s'!" % os.path.basename(output_filepath))

    else:
        log.error("Output file path is neither a file or a directory!")
        exit(2)


if __name__ == '__main__':
    main()
