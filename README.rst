todoist-org-mode
================

Convert Todoist projects into Org mode files


What this project does
----------------------

This is a `Python language <https://www.python.org/>`__ project with code to retrieve
Todoist projects, sections and items using the Todoist `Sync API (v8)
<https://doist.github.io/todoist-api/sync/v8/>`__ and convert them into Org mode
headings to be written to files.

`Todoist <https://todoist.com/>`__ is an application for maintaining to-do lists and
planning projects. `Org mode <https://orgmode.org/>`__ is a `GNU Emacs
<https://www.gnu.org/software/emacs/>`__ major mode for convenient plain text markup
and much more, including maintaining to-do lists and planning projects.

*todoist-org-mode* Python files:

- ``todoist2org`` - Library for generating Org mode headings from Todoist projects,
  sections and items.
- ``todoist2org_convert`` - Command-line (CLI) program to retrieve Todoist projects,
  sections and items, convert them to Org mode headings using ``todoist2org`` and
  write each heading to stdout or to the specified output file.

No part of this project modifies remote Todoist user data, it is only retrieved and
converted locally.


Dependencies
------------

- `python-dateutil <https://dateutil.readthedocs.io/en/stable/>`__
- `pytz <https://pypi.python.org/pypi/pytz>`__
- `todoist-python <https://github.com/doist/todoist-python>`__


Using this project
------------------

To use this project, follow the steps below.

#. Clone or download and extract the repository.

   .. code:: shell

      git clone https://github.com/Danesprite/todoist-org-mode.git

#. Open a command prompt or terminal in the repository's root directory.

   .. code:: shell

      cd todoist-org-mode

#. Install the required dependencies.

   .. code:: shell

      pip install python-dateutil pytz todoist-python


``todoist2org_convert`` program usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``todoist2org_convert``, passing your Todoist API token and an optional output
file path as the arguments. Your API token can be found under Settings->Integrations.

.. code:: shell

   # Either convert and print all headings to stdout.
   python todoist2org_convert.py 0123456789abcdef0123456789abcdef01234567

   # Or convert and write all headings to output.org.
   python todoist2org_convert.py 0123456789abcdef0123456789abcdef01234567 -o output.org


``todoist2org`` library usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``todoist2org`` library can be used for custom conversion of Todoist projects,
sections and/or items. For example, it could be used to convert all items in the
special Inbox project and write an Inbox.org file:

.. code:: Python

   import todoist
   import todoist2org

   # Use the API token to sync user resources.
   api_token = "0123456789abcdef0123456789abcdef01234567"
   api = todoist.TodoistAPI(api_token)
   api.sync()

   # Assume the Inbox project is first.
   project = api.state["projects"][0]
   project_id = project["id"]

   # Write an Org mode file header followed by each generated heading to Inbox.org.
   with open("Inbox.org", "w") as f:
       for line in todoist2org.generate_file_header(api.state, "Inbox"):
           f.write(line + "\n")
       f.write("\n")
       for heading in todoist2org.generate_project_headings(api.state, project_id):
           f.write(heading + "\n")


Limitations
-----------

- This project does **not** work in the other direction, i.e. it will **not** parse
  Org mode files and update Todoist with the equivalent projects, sections and items.

- Conversion of recurring due dates is **not** supported. Project items with
  recurring due dates will be tagged with ``:IS_RECURRING:`` for manual user
  conversion. Warnings will be logged for every item encountered that has a recurring
  due date. See the `Org Manual Repeated Tasks
  <https://orgmode.org/manual/Repeated-tasks.html>`__ section for how to specify
  recurring due dates in Org mode.

- Project notes, item notes/comments, calendar feeds, reminders and templates are
  **not** brought over in the conversion process.

- Archived projects are not included by default. There is an optional CLI ``-a`` /
  ``--include-archived`` argument and equivalent library function parameter that can
  be used to include archived projects. If these are used, archived projects are
  tagged with ``:IS_ARCHIVED:`` and output in roughly their original positions in the
  projects list. They are not filed under a separate heading.


License
-------

This is free software licensed under the MIT licence.
