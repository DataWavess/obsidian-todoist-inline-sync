from contact.tm_api import todoist_update_task
from convert.task_converters import convert_tm_to_nm_task, process_task_for_submission_to_tm

def update_task_to_todoist(nm_task: dict) -> dict:
    """
    Pushes the information from a note manager task to the 
    todo list manager where the task already exists.
    
    Returns
    - A td_nm_task, a task that has metadata from the todo manager,
    task is formatted as a note_manager task
    """
    tm_nm_task = process_task_for_submission_to_tm(nm_task)
    tm_task = todoist_update_task(nm_task.get('task_tm_link_id'), tm_nm_task)
    tm_nm_task = convert_tm_to_nm_task(tm_task, nm_task)
    return tm_nm_task
