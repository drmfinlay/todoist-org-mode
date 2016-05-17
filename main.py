#!/usr/bin/python2

def get_file_lines(filepath):
    with open(filepath, 'r') as f:
        lines = [line.rstrip('\n') for line in f]
    return lines

def contains_date(task):
    """
    Returns True if [[date *]] is matched in the task string.
    >>> contains_date('[[date today]]')
    True
    >>> contains_date('[[date 05/05/16]]')
    True
    >>> contains_date('[[date 05/05/16')
    False
    >>> contains_date('date 05/05/16]]')
    False
    >>> contains_date('[[ 05/05/16]]')
    False
    >>> contains_date('[[date ]]')
    False

    """
    pass

def build_task_tree(task_list):
    tree = []
    for task in task_list:
        # Check what information should be added to org-mode file
        pass

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=False)
