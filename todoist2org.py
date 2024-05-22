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
'Sync' API v9.

"""

from datetime import datetime
import logging
import re
import requests

from dateutil import parser as date_parser
import pytz


#------------------------------------------------------------------------------------
# Sync Todoist data utility function.

def sync_todoist_state(api_token):
    """ Retrieve Todoist user resources (state) associated with an API token. """
    headers = {"Authorization": "Bearer %s" % api_token}
    data = {"sync_token": '*', "resource_types": '["all"]'}
    r = requests.post("https://api.todoist.com/sync/v9/sync",
                      headers=headers, data=data)
    return r.json()


#------------------------------------------------------------------------------------
# Todoist to org conversion utilities.

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


def generate_all_headings(state, include_archived):
    """
    Generate Org mode headings for all Todoist projects, sections and items.

    This is a generator function that returns strings in Org mode format.

    :param state: Todoist 'Sync' API state dictionary
    :type state: dict
    :param include_archived: whether to include archived projects or sections in the
        output
    :type include_archived: bool
    :returns: heading strings
    """
    # Prepare required dictionaries.
    # Project ID -> Project dictionary.
    projects_dict = {project["id"]: project for project in state["projects"]}

    # Project ID -> Sections dictionary.
    # Put sections into lists associated with each project.
    section_list_dict = {project["id"]: [] for project in state["projects"]}
    for section in state["sections"]:
        # Skip sections of deleted projects.
        project_id = section["project_id"]
        if project_id not in section_list_dict:
            continue

        section_list_dict[project_id].append(section)

    # Project ID -> Items dictionary.
    # Put items into lists associated with each project.
    item_list_dict = {project["id"]: [] for project in state["projects"]}
    for item in state["items"]:
        # Skip items of deleted projects.
        project_id = item["project_id"]
        if project_id not in item_list_dict:
            continue

        item_list_dict[project_id].append(item)

    # Label name -> label dictionary.
    label_dict = {label["name"]: label for label in state["labels"]}

    # Log a warning if any tasks have recurring due dates.
    _warn_about_recurring_due_dates(state["items"])

    # Generate and yield Org mode headings.
    for project in state["projects"]:
        # Skip archived projects if requested.
        if not include_archived and project["is_archived"]:
            continue

        # Calculate the project's indentation level.
        project_level = get_object_level(project["id"], projects_dict)

        # Generate the root project heading.
        yield get_project_root_heading(project, project_level)

        # Generate the subheadings for sections and items.
        project_items = item_list_dict[project["id"]]
        project_sections = section_list_dict[project["id"]]
        for heading in generate_project_subheadings(state, project_items,
                                                    project_sections, project_level,
                                                    label_dict,
                                                    include_archived):
            yield heading


def generate_project_headings(state, project_id, include_archived):
    """
    Generate Org mode headings for the specified Todoist project, including headings
    for all associated sections and items.

    This is a generator function that returns strings in Org mode format.

    :param state: Todoist 'Sync' API state dictionary
    :type state: dict
    :param project_id: Todoist project ID
    :type project_id: str
    :param include_archived: whether to include archived sections in the output
    :type include_archived: bool
    :returns: heading strings
    """
    # Prepare required dictionaries and lists.
    projects_dict = {project["id"]: project for project in state["projects"]}
    project_sections = [section for section in state["sections"]
                        if section["project_id"] == project_id]
    project_items = [item for item in state["items"]
                     if item["project_id"] == project_id]
    label_dict = {label["id"]: label for label in state["labels"]}

    # Log a warning if any tasks have recurring due dates.
    _warn_about_recurring_due_dates(project_items)

    # Get the project and calculate the indentation level.
    project = projects_dict[project_id]
    project_level = get_object_level(project_id, projects_dict)

    # Generate the root project heading.
    yield get_project_root_heading(project, project_level)

    # Generate the subheadings for sections and items.
    for heading in generate_project_subheadings(state, project_items,
                                                project_sections, project_level,
                                                label_dict, include_archived):
        yield heading


def generate_project_subheadings(state, project_items, project_sections,
                                 project_level, label_dict, include_archived):
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
    :param label_dict: dictionary of label name to label
    :type label_dict: dict
    :param include_archived: whether to include archived sections in the output
    :type include_archived: bool
    :returns: subheading strings
    """
    # pylint: disable=too-many-arguments
    # Sort the project sections list by section order.
    project_sections.sort(key=lambda section: section["section_order"])

    # Prepare lists of items for each section. Include a list for items that don't
    # belong to any section.
    section_item_lists = {section["id"]: [] for section in project_sections}
    section_item_lists[None] = []
    for item in project_items:
        section_item_lists[item["section_id"]].append(item)

    # Prepare a dictionary of item parent IDs to child items.
    item_children = {item["id"]: [] for item in project_items}
    for item in project_items:
        parent_id = item["parent_id"]
        if parent_id:
            item_children[parent_id].append(item)

    # Generate subheadings from project sections and items in order with items that
    # don't belong to any section first.
    for section in [None] + project_sections:
        if section is None:
            section_id = None
            section_level = project_level
        else:
            section_id = section["id"]
            section_level = project_level + 1

            # Skip archived sections if requested.
            if not include_archived and section["is_archived"]:
                continue

            # Generate a subheading for the current item's section.
            yield get_section_heading(state, section, section_level)

        # Generate item subheadings.
        # Pass only top-level items in this section with no parent items. Child items
        # will be handled recursively.
        items = [item for item in section_item_lists[section_id]
                 if item["parent_id"] is None]
        for heading in generate_item_headings(state, items, section_level + 1,
                                              item_children, label_dict):
            yield heading


def generate_item_headings(state, items, heading_level, item_children,
                           label_dict):
    """
    Generate Org mode headings for the specified items and any child items.

    This is a generator function that returns strings in Org mode format.

    :param state: Todoist 'Sync' API state dictionary
    :type state: dict
    :param items: list of items to generate headings for
    :type items: list
    :param heading_level: heading indentation level
    :type heading_level: int
    :param item_children: dictionary of item parent IDs to items
    :type item_children: dict
    :param label_dict: dictionary of label name to label
    :type label_dict: dict
    :returns: heading strings
    """
    # Sort the items list by child order.
    items.sort(key=lambda i: i["child_order"])
    for item in items:
        # Generate a heading for this item.
        yield get_item_heading(state, item, heading_level, label_dict)

        # Generate headings for any child items recursively.
        children = item_children[item["id"]]
        for heading in generate_item_headings(state, children, heading_level + 1,
                                              item_children, label_dict):
            yield heading


def get_object_level(object_id, objects):
    """
    Get the indentation level of the specified project or item. This will typically
    be an integer between 1 and 4.

    If this function is used to calculate an item's level, it will **not** calculate
    and add the project level too. A separate call is required for that.

    :param object_id: Todoist project or item ID
    :type object_id: str
    :param objects: dictionary of object IDs to objects
    :type objects: dict
    :returns: object indentation level
    :rtype: int
    """
    # Check if this project or item has a parent. If it doesn't, then it is a level 1
    # project or item. Otherwise, the indentation level is 1 plus the parent object's
    # level.
    obj = objects[object_id]
    parent_id = obj["parent_id"]
    if parent_id is None:
        return 1
    return 1 + get_object_level(parent_id, objects)


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
    # NOTE This doesn't work in Python 2.7.
    tz = pytz.timezone(timezone)
    dateobj = dateobj.astimezone(tz)

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


def convert_markdown_to_org(content):
    """
    Convert markdown in a content string to the equivalent Org format.

    The original string will be returned if no conversion is necessary.

    Currently, this method only converts hyperlinks.

    :param content: content string
    :type content: str
    :returns: converted content string
    :rtype: str
    """
    # Convert and replace any markdown hyperlinks in the content string.
    md_hyperlink_p = re.compile(r"(\[(?!\]).+?\])(\((?!\)).+?\))")
    for match in md_hyperlink_p.finditer(content):
        link_text = match.group(1)[1:-1]
        linkurl = match.group(2)[1:-1]
        org_hyperlink = "[[%s][%s]]" % (linkurl, link_text)
        content = content.replace(match.group(0), org_hyperlink)

    return content


def get_heading_lines(heading_level, todo_state, content, priority=1,
                      tags=None, timestamps=None, description="",
                      **properties):
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
    :param description: description for the heading
    :type description: str
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
    todo_state_str = todo_state + " " if todo_state else ""
    tags_str = " :%s:" % ":".join(tags) if tags else ""

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

    # Yield indented description lines if necessary.
    if description:
        for line in description.split("\n"):
            if not line:
                yield ""
            else:
                yield "%s %s" % (spaces, line)


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
    # Add a special :ARCHIVED: tag if this project is archived.
    tags = ["ARCHIVED"] if project["is_archived"] else []

    # Return each line of the heading with a newline afterwards.
    project_name = project["name"]
    return "\n".join(
        get_heading_lines(heading_level, "", project_name, tags=tags,
                          CATEGORY=project_name)
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
    added_at_timestamp = get_org_timestamp(section["added_at"], user_tz, False)

    # Add a special :ARCHIVED: tag if this section is archived.
    tags = ["ARCHIVED"] if section["is_archived"] else []

    # Return each line of the heading with a newline afterwards.
    return "\n".join(
        get_heading_lines(heading_level, "", section["name"], tags=tags,
                          CREATED=added_at_timestamp)
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
    :param labels: dictionary of label name to label
    :type labels: dict
    :returns: heading string
    :rtype: str
    """
    # Gather info about this item.
    user_tz = state["user"]["tz_info"]["timezone"]
    added_at_timestamp = get_org_timestamp(item["added_at"], user_tz, False)
    completed_at = item["completed_at"]
    due_info = item["due"]
    priority = item["priority"]
    todo_state = "DONE" if completed_at else "TODO"

    # Retrieve the item's content and description. Convert markdown as necessary.
    content = convert_markdown_to_org(item["content"])
    description = convert_markdown_to_org(item["description"])

    # Use an ordered list of this item's labels as Org tags.
    item_labels = [labels[label_name] for label_name in item["labels"]]
    item_labels.sort(key=lambda l: l["item_order"])
    tags = [label["name"] for label in item_labels]

    # Get the CLOSED/SCHEDULED timestamps if necessary.
    timestamps = HeadingTimestamps()
    if completed_at:
        # Add the inactive CLOSED timestamp.
        timestamps.closed = get_org_timestamp(completed_at, user_tz, False)

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
        get_heading_lines(heading_level, todo_state, content, priority,
                          tags, timestamps, description,
                          CREATED=added_at_timestamp)
    ) + "\n"
