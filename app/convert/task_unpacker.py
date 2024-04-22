import hashlib
from contact.tm_api import get_completed_resources
from datetime import datetime
import json
from variables import app_location
import os 

def unpack_nm_note_task(notes_nm_task: dict, task_type='all') -> dict:
    """
    Given a note vault object of notes and their task will return just the task as a list of dicts.

    Return
    - A dict, each entry represents a task, the key is a hash of the task's file and line number as the key.
    """
    if task_type not in ('recurring', 'all'):
        raise ValueError('Invalid task_type')
    nm_tasks = {}
    for note, tasks  in notes_nm_task.items():
        for task in tasks:
            if task_type == 'recurring':
                if task.get('task_recurrence'):
                    nm_id = task.get('task_tm_link_id')
                    if nm_id and nm_id in nm_tasks:
                        nm_tasks[str(nm_id)].append(task)
                    elif nm_id:
                        nm_tasks[str(nm_id)] = [task]
            else:
                nm_id = str(task.get('task_file_location')) + ':' + str(task.get('task_md_line'))
                hashed_key = hashlib.sha256(nm_id.encode('utf-8'))
                nm_tasks[hashed_key.digest()] = task
                    
    return nm_tasks


def get_missing_recurring_completions(recurring_nm_tasks: dict):
    """
    Given a list of recurring nm_task will calculate the missing dates that need to be added to the 
    note manager.

    Return:
    - A dict of completion dates attached to a tm_task that need to be added to the note manager
    """
    completed_tm_task = get_completed_resources('items')

    # create dict of all recurrence ids
    recurring_task_ids = {k: {} for k, v in recurring_nm_tasks.items()}

    # aggregate completed dates in todo manager from recurring task
    tm_completion_log = {}
    for completes in completed_tm_task:
        task_complete_id = completes.get('task_id')
        complete_date = datetime.strptime(completes.get('completed_at'), '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d')
        if task_complete_id in tm_completion_log:
            tm_completion_log[task_complete_id].append(complete_date)
        else:
            tm_completion_log[task_complete_id] = [complete_date]

    # aggregate completed dates in note manager from recurring task
    nm_completion_log = {} 
    for key, completes in recurring_nm_tasks.items():
        for recurring_task in completes:
            task_complete_id = recurring_task.get('task_tm_link_id')
            complete_date = recurring_task.get('task_dates').get('completed_date')
            if complete_date:
                if task_complete_id in nm_completion_log:
                    nm_completion_log[task_complete_id].append(complete_date)
                else:
                    nm_completion_log[task_complete_id] = [complete_date]

    # Compare the completions within the todo manager with the completions from the note manager
    # Add any missing completions to be processed further
    missing_recurring_task_history = {}
    for recurring_task_id, recurring_task_completions  in recurring_task_ids.items():
        nm_completions = nm_completion_log.get(recurring_task_id)
        tm_completions = tm_completion_log.get(recurring_task_id)
        if tm_completions:
            missing_completions = [completion_date for completion_date in tm_completions if completion_date not in (nm_completions or [])]
            if missing_completions:
                missing_recurring_task_history[recurring_task_id] = {}
                missing_recurring_task_history[recurring_task_id]['task_completions'] = missing_completions

    # Add the due date from todo manger to the the dict containing the missing completions.
    # This is to be able to determine what the new due date for the task is.
    with open(os.path.join(app_location, 'tm_tasks.json'), 'r') as f:
        data = json.load(f)
        
    for task_key, task in missing_recurring_task_history.items():
        tm_task = data.get(task_key)
        active_due_date = tm_task.get('due', {}).get('date')
        task['task_active_due_date'] = active_due_date
    
    with open(os.path.join(app_location, 'missing_recurring_task_history.json'), 'w') as f:
        json.dump(missing_recurring_task_history, f)

    return missing_recurring_task_history

