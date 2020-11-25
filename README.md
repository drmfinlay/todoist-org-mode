# todoist-org-mode
Transform Todoist projects into Org-mode files

## What it does
Given a Todoist API token, main.py will retrieve project, task and comment data from Todoist using the official API available [here](https://developer.todoist.com/). The program will then transform this data into Emacs Org format into the file you specify.

## Python Library Dependencies
  - [dateutil](https://dateutil.readthedocs.io/en/stable/)
  - [parse](https://pypi.python.org/pypi/parse)
  - [pytz](https://pypi.python.org/pypi/pytz)
  - urllib
  - datetime

## How to run the program
Run main.py with the following arguments:
  1. Todoist API token
  2. Output file path
  3. [Optional] Use either -a or --append-output to append output to the file instead of overwriting it

## License
This is free software licensed under the MIT licence.
