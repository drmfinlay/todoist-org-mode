#!/usr/bin/python3
#
# MIT License
#
# Copyright (c) 2016 Dane Finlay
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

"""
todoist2org_convert

This program retrieves Todoist projects, sections and items using the 'Sync' API
(v8) and converts them into Org mode headings. Each heading is written to stdout or
to the specified output file. An Org mode file header is written before the headings.

"""

import argparse
import logging
import os
import sys

import todoist

import todoist2org


def _valid_api_token(string):  # argparse helper function
    if len(string) != 40:
        msg = "%r is not a valid API token" % string
        raise argparse.ArgumentTypeError(msg)
    return string


def _main():
    # Define command-line arguments.
    parser = argparse.ArgumentParser(
        description="Retrieve and convert Todoist projects, sections and items into "
                    "Org mode headings and write them to stdout or to the specified "
                    "output file."
    )
    parser.add_argument(
        "api_token", type=_valid_api_token,
        help="40 character Todoist API token found under Settings->Integrations."
    )
    parser.add_argument(
        "-o", "--output-file", type=argparse.FileType("w"),
        help="Output file path."
    )

    # Parse command-line arguments from sys.argv.
    args = parser.parse_args()

    # Set up logging.
    logging.basicConfig(format="%(levelname)s: %(message)s")
    log = logging.getLogger()

    # Use the API token to sync user resources.
    api = todoist.TodoistAPI(args.api_token)
    sync_response = api.sync()

    # Check if the sync was unsuccessful. This can happen if the API token was
    # invalid.
    if "sync_token" not in sync_response:
        log.error("Failed to sync Todoist data. Check your API token.")
        exit(1)

    # If a file path was specified, then write to that file. Otherwise, write to
    # stdout.
    output_file = args.output_file
    if output_file and output_file.name != "<stdout>":
        # Get the title to use in the file header.
        base = os.path.basename(output_file.name)
        title = os.path.splitext(base)[0]
    else:
        title = "Converted Todoist Projects"
        output_file = sys.stdout

    # Use the retrieved data to generate an Org mode file header followed by each
    # heading.
    with output_file as out:
        for line in todoist2org.generate_file_header(api.state, title):
            out.write(line + "\n")
        out.write("\n")
        for heading in todoist2org.generate_all_headings(api.state):
            out.write(heading + "\n")


if __name__ == '__main__':
    _main()
