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
todoist2org

This module is a library for generating Org mode headings from Todoist projects,
sections and items. It is intended to be used with data retrieved via the Todoist
'Sync' API v8.

"""

from datetime import datetime
import logging

from dateutil import parser as date_parser
import pytz


class HeadingTimestamps:
    """ Container for optional Org heading timestamps used on line two. """

    def __init__(self, closed=None, scheduled=None, deadline=None):
        self.closed = closed
        self.scheduled = scheduled
        self.deadline = deadline

    def __nonzero__(self):
        return bool(self.closed or self.scheduled or self.deadline)

    def __bool__(self):
        return self.__nonzero__()


def _warn_about_recurring_due_dates(items):
    any_recurring_due_dates = any([
        item["due"]["is_recurring"] for item in items
        if item["due"] is not None
    ])
    if any_recurring_due_dates:
        log = logging.getLogger()
        log.warning("Automatic conversion of recurring due dates is NOT supported. "
                    "Project items with recurring due dates will be tagged with "
                    ":IS_RECURRING: for manual user conversion.\nSee the Org Manual "
                    "'Repeated Tasks' section for how to do this: "
                    "https://orgmode.org/manual/Repeated-tasks.html")


def generate_file_header(state, title):
    """
    Generate an Org mode file header using Todoist user data and the specified title.

    This is a generator function that returns Org mode file header strings.

    :param state: Todoist 'Sync' API state dictionary
    :type state: dict
    :param title: title of the Org mode file
    :type title: str
    :returns: file heading strings
    """
    yield "#+AUTHOR: %s" % state["user"]["full_name"]
    yield "#+DATE: %s" % datetime.now().strftime("[%Y-%m-%d %a %H:%M]")
    yield "#+TITLE: %s" % title


def generate_all_headings(state):
    """
    Generate Org mode headings for all Todoist projects, sections and items.

    This is a generator function that returns strings in Org mode format.

    :param state: Todoist 'Sync' API state dictionary
    :type state: dict
    :returns: heading strings
    """
    # Prepare required dictionaries.
    # Project ID -> Project dictionary.
    projects_dict = {project["id"]: project for project in state["projects"]}

    # Project ID -> Sections dictionary.
    # Put sections into lists associated with each project.
    section_list_dict = {project["id"]: [] for project in state["projects"]}
    for section in state["sections"]:
        section_list_dict[section["project_id"]].append(section)

    # Project ID -> Items dictionary.
    # Put items into lists associated with each project.
    item_list_dict = {project["id"]: [] for project in state["projects"]}
    for item in state["items"]:
        item_list_dict[item["project_id"]].append(item)

    # Label ID -> Label names dictionary.
    label_names_dict = {label["id"]: label for label in state["labels"]}

    # Log a warning if any tasks have recurring due dates.
    _warn_about_recurring_due_dates(state["items"])

    # Generate and yield Org mode headings.
    for project in state["projects"]:
        # Calculate the project's indentation level.
        project_level = get_project_level(project["id"], projects_dict)

        # Generate the root project heading.
        yield get_project_root_heading(project, project_level)

        # Generate the subheadings for sections and items.
        project_items = item_list_dict[project["id"]]
        project_sections = section_list_dict[project["id"]]
        for heading in generate_project_subheadings(state, project_items,
                                                    project_sections, project_level,
                                                    label_names_dict):
            yield heading


def generate_project_headings(state, project_id):
    """
    Generate Org mode headings for the specified Todoist project, including headings
    for all associated sections and items.

    This is a generator function that returns strings in Org mode format.

    :param state: Todoist 'Sync' API state dictionary
    :type state: dict
    :param project_id: Todoist project ID
    :type project_id: int
    :returns: heading strings
    """
    # Prepare required dictionaries and lists.
    projects_dict = {project["id"]: project for project in state["projects"]}
    project_sections = [section for section in state["sections"]
                        if section["project_id"] == project_id]
    project_items = [item for item in state["items"]
                     if item["project_id"] == project_id]
    label_names_dict = {label["id"]: label for label in state["labels"]}

    # Log a warning if any tasks have recurring due dates.
    _warn_about_recurring_due_dates(project_items)

    # Get the project and calculate the indentation level.
    project = projects_dict[project_id]
    project_level = get_project_level(project_id, projects_dict)

    # Generate the root project heading.
    yield get_project_root_heading(project, project_level)

    # Generate the subheadings for sections and items.
    for heading in generate_project_subheadings(state, project_items,
                                                project_sections, project_level,
                                                label_names_dict):
        yield heading


def generate_project_subheadings(state, project_items, project_sections,
                                 project_level, label_names_dict):
    """
    Generate Org mode subheadings for the specified project.

    This is a generator function that returns strings in Org mode format.

    :param state: Todoist 'Sync' API state dictionary
    :type state: dict
    :param project_items: list of items in this project
    :type project_items: list
    :param project_sections: list of sections in this project
    :type project_sections: list
    :param project_level: project indentation level
    :type project_level: int
    :param label_names_dict: dictionary of label IDs to label names
    :type label_names_dict: dict
    :returns: subheading strings
    """
    # Sort the project sections list by section order.
    project_sections.sort(key=lambda section: section["section_order"])

    # Prepare lists of items for each section. Include a list for items that don't
    # belong to any section.
    section_item_lists = {section["id"]: [] for section in project_sections}
    section_item_lists[None] = []
    for item in project_items:
        section_item_lists[item["section_id"]].append(item)

    # Generate subheadings from project sections and items in order with items that
    # don't belong to any section first.
    for section in [None] + project_sections:
        if section is None:
            section_id = None
            item_level = project_level + 1
        else:
            section_id = section["id"]
            item_level = project_level + 2

            # Generate a subheading for the current item's section.
            yield get_section_heading(state, section, project_level + 1)

        # Generate item subheadings.
        for item in section_item_lists[section_id]:
            yield get_item_heading(state, item, item_level, label_names_dict)


def get_project_level(project_id, projects):
    """
    Get the indentation level of the specified project. This will be an integer
    between 1 and 4.

    :param project_id: Todoist project ID
    :type project_id: int
    :param projects: dictionary of project IDs to Project objects
    :type projects: dict
    :returns: project indentation level
    :rtype: int
    """
    # Check if this project has a parent. If it doesn't, then it is a level 1
    # project. Otherwise, the indentation level is 1 plus the parent project's level.
    project = projects[project_id]
    parent_id = project["parent_id"]
    if parent_id is None:
        return 1
    return 1 + get_project_level(parent_id, projects)


def get_org_timestamp(timestamp, timezone, active):
    """
    Get a local Org mode timestamp string from the specified timestamp and timezone.

    :param timestamp: timestamp string
    :type timestamp: str
    :param timezone: timezone to use
    :type timezone: str
    :param active: Whether to return an active or inactive Org timestamp.
    :type active: bool
    :returns: Org timestamp string
    :rtype: str
    """
    # Parse the timestamp.
    dateobj = date_parser.parse(timestamp)

    # Convert from UTC to specified timezone.
    dateobj = dateobj.astimezone(pytz.timezone(timezone))

    # Handle full-day dates.
    if "T" not in timestamp:
        time_format_string = "<%Y-%m-%d %a>"

    # Handle floating and fixed timezone due dates with time specified.
    else:
        time_format_string = "<%Y-%m-%d %a %H:%M>"

    # Handle inactive timestamps.
    if not active:
        time_format_string = time_format_string.replace("<", "[").replace(">", "]")

    # Return the timestamp.
    return dateobj.strftime(time_format_string)


def get_heading_lines(heading_level, todo_state, content, priority=1,
                      tags=None, timestamps=None, **properties):
    """
    Get each line of an Org mode heading.

    This is a generator function.

    :param heading_level: heading indentation level
    :type heading_level: int
    :param todo_state: current state of this item
    :type todo_state: str
    :param content: first line content
    :type content: str
    :param priority: int between 1 and 4 indicating priority (4 = highest priority)
    :type priority: int
    :param tags: list of strings to use as heading tags
    :type tags: list
    :param timestamps: timestamps to use on line 2 (if any)
    :type timestamps: HeadingTimestamps
    :param properties: keyword names and values representing heading properties
    :returns: heading lines
    """
    # pylint: disable=too-many-locals,too-many-arguments
    if tags is None:
        tags = ()

    # Calculate the number of stars and spaces using the heading level.
    stars = heading_level * "*"
    spaces = heading_level * " "

    # Get line components ready.
    priority_str = {
        4: "[#A] ",
        3: "[#B] ",
        2: "[#C] ",
        1: "",  # no priority
    }[priority]
    tags_str = " :%s:" % ":".join(tags) if tags else ""
    todo_state_str = todo_state + " " if todo_state else ""

    # Construct and yield the first line of the heading.
    yield "%s %s%s%s%s" % (stars, todo_state_str, priority_str, content, tags_str)

    # Yield the CLOSED/SCHEDULED/DEADLINE line if necessary.
    if timestamps:
        closed = timestamps.closed
        scheduled = timestamps.scheduled
        deadline = timestamps.deadline
        timestamps_list = []
        if closed:
            timestamps_list.append("CLOSED: " + closed)
        if scheduled:
            timestamps_list.append("SCHEDULED: " + scheduled)
        if deadline:
            timestamps_list.append("DEADLINE: " + deadline)
        yield "%s %s" % (spaces, " ".join(timestamps_list))

    # Yield property lines if necessary.
    if properties:
        yield "%s :PROPERTIES:" % spaces
        for name, value in properties.items():
            yield "%s :%s: %s" % (spaces, name, value)
        yield "%s :END:" % spaces


def get_project_root_heading(project, heading_level):
    """
    Get the root Org mode heading string for the specified project.

    :param project: Todoist Project object
    :type project: Project
    :param heading_level: heading indentation level
    :type heading_level: int
    :returns: heading string
    :rtype: str
    """
    # Return each line of the heading with a newline afterwards.
    project_name = project["name"]
    return "\n".join(
        get_heading_lines(heading_level, "", project_name, CATEGORY=project_name)
    ) + "\n"


def get_section_heading(state, section, heading_level):
    """
    Get the Org mode heading string for the specified section.

    :param state: Todoist 'Sync' API state dict
    :type state: dict
    :param section: Todoist Section object
    :type section: Section
    :param heading_level: heading indentation level
    :type heading_level: int
    :returns: heading string
    :rtype: str
    """
    # Gather info about this section.
    user_tz = state["user"]["tz_info"]["timezone"]
    date_added_timestamp = get_org_timestamp(section["date_added"], user_tz, False)

    # Return each line of the heading with a newline afterwards.
    return "\n".join(
        get_heading_lines(heading_level, "", section["name"],
                          CREATED=date_added_timestamp)
    ) + "\n"


def get_item_heading(state, item, heading_level, labels):
    """
    Get the Org mode heading string for the specified item.

    :param state: Todoist 'Sync' API state dict
    :type state: dict
    :param item: Todoist Item object
    :type item: Item
    :param heading_level: heading indentation level
    :type heading_level: int
    :param labels: dictionary of label IDs to label names
    :type labels: dict
    :returns: heading string
    :rtype: str
    """
    # Gather info about this item.
    user_tz = state["user"]["tz_info"]["timezone"]
    date_added_timestamp = get_org_timestamp(item["date_added"], user_tz, False)
    date_completed = item["date_completed"]
    due_info = item["due"]
    priority = item["priority"]
    todo_state = "DONE" if date_completed else "TODO"
    tags = [labels[label_id] for label_id in item["labels"]]

    # Get the CLOSED/SCHEDULED timestamps if necessary.
    timestamps = HeadingTimestamps()
    if date_completed:
        # Add the inactive CLOSED timestamp.
        timestamps.closed = get_org_timestamp(date_completed, user_tz, False)

    if due_info:
        # Use the due date timezone if it is specified, otherwise use the user
        # timezone.
        due_date_tz = due_info["timezone"] if due_info["timezone"] else user_tz

        # Recurring due date support is difficult to implement, especially for every
        # language Todoist supports. Instead of undertaking this arduous task, we add
        # a special Org mode tag to the heading and log a warning message with the
        # user date string informing the user that this has to be done manually.
        if due_info["is_recurring"]:
            tags.append("IS_RECURRING")
            log = logging.getLogger()
            log.warning('Item with content %r has recurring due date %r.',
                        item["content"], due_info["string"])

        # Add the active SCHEDULED timestamp.
        timestamps.scheduled = get_org_timestamp(due_info["date"], due_date_tz, True)

    # Return each line of the heading with a newline afterwards.
    return "\n".join(
        get_heading_lines(heading_level, todo_state, item["content"], priority,
                          tags, timestamps, CREATED=date_added_timestamp)
    ) + "\n"
