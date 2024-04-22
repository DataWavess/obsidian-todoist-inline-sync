from convert.task_converters import convert_tm_to_nm_task, process_task_for_submission_to_tm
from contact.tm_api import todoist_add_task_sync


# INFO: create tuple for creating todoist task
td_adding_task_keys_used = [
    "content", # task name
    "description", # the whole line
    "project_id", # default to inbox
    "due", # due object
            # ...
    "priority", # the values are inversed. 4 is very urgent in the api values.
    "parent_id", # set to null for root task #TODO:?: change this so its not a child task for applicable task.
    # "child_order",
    # "section_id", 
    # "day_order", 
    # "collapsed", 
    "labels", # tags
    # "assigned_by_uid", 
    # "responsible_uid",
    # "auto_reminder", 
    # "auto_parse_labels", 
    # "duration" 
]

def add_task_to_todoist(nm_task:dict) -> dict:
    """
    Submits a note task to todo manager.
    
    Returns:
    - A td_nm_task, a task that has metadata from the todo manager,
    task is formatted as a note_manager task
    """
    task_name = nm_task['task_name']
    tm_task_proxy = process_task_for_submission_to_tm(nm_task)
    tm_task = todoist_add_task_sync(task_name, tm_task_proxy)
    tm_nm_task = convert_tm_to_nm_task(tm_task.to_dict(), nm_task)
    return tm_nm_task