from contact.tm_api import todoist_complete_task


def complete_task_to_todoist(nm_task:dict) -> dict:
    """
    Completes a task in todo manager.
    
    Returns:
    - The same task with a completion status
    """
    success_status = todoist_complete_task(nm_task['task_tm_link_id'])
    nm_task['task_checkbox_status'] = 'close'
    return nm_task
