from datetime import datetime, timedelta
import re
import os
import json
import uuid
from variables import sync_logic, frontmatter_modified_date_field, frontmatter_modified_date_regex, app_location
from contact.create_task_to_todoist import add_task_to_todoist
from contact.update_task_to_todoist import update_task_to_todoist
from contact.complete_task_to_todoist import complete_task_to_todoist
from contact.tm_api import push_batched_commands
from writeback.push_task_to_nm import push_task_to_nm
from convert.task_converters import process_task_for_submission_to_tm, process_batched_nm_task_to_nm_task



batched_task_for_tm = {}
def sync_task_to_tm(nm_notes:dict, current_run_time:object, tm_sync_type='batch') -> dict:
    """
    Processes a list of notes, extracting associated tasks from a dictionary, 
    and then submits these tasks to the note manager with the appropriate context."

    Parameters:
    - A full list of notes contained in a vault and their associated task.
    
    Returns:
    - None
    """
    global batched_task_for_tm
    all_tasks_processed = []
    # read in todo manager for status determination
    with open(os.path.join(app_location, 'tm_tasks.json'), 'r') as f:
        tm_tasks = json.load(f)
    
    if tm_sync_type == 'rest':
        for note in nm_notes:
            task_notes_processed = []
            for nm_task in nm_notes[note]:
                determine_task_change_status(nm_task, current_run_time, tm_tasks)
                task_notes_processed.append(push_task_to_todoist(nm_task))
            # push processed todos to note manager
            if task_notes_processed:
                push_task_to_nm(task_notes_processed, note)
            all_tasks_processed.append(task_notes_processed)
    elif tm_sync_type == 'batch': 
        for note in nm_notes:
            task_notes_processed = []
            batched_task = []
            non_batched_task = []
            uuid_batched_task = []
            # process task in current note
            for nm_task in nm_notes[note]:
                determine_task_change_status(nm_task, current_run_time, tm_tasks)
                prepared_batch_task = push_task_to_todoist(nm_task, tm_sync_type)
                if prepared_batch_task:
                    batched_task.append(prepared_batch_task)
                else:
                    task_notes_processed.append(nm_task)

            uuid_batched_task = {task.get('uuid'):task for task in batched_task}
            # push batched task to todo manager
            for i in range(0, len(batched_task), 100):
                upload_batch = batched_task[i:i+100]
                push_status_dict = push_batched_commands(upload_batch)
                sync_status_dict = push_status_dict.get('sync_status')
                print('push_status_dict is:')
                print(push_status_dict)
                print()
                print('sync_statu dict\n', sync_status_dict)
                print()
                # update task with its pushed status
                for uuid, uuid_status in sync_status_dict.items():
                    print('current uuid', uuid)
                    task = batched_task_for_tm.get(uuid)
                    print()
                    print('this task is pulled from batched task for tm')
                    print(task)
                    task['task_batch_synced_status'] = uuid_status
                    print('uuid status:', uuid_status)
                    if task['task_tm_status'] == 'new':
                        print('this is a new task')
                        print(uuid)
                        print(push_status_dict.get('temp_id_mapping'))
                        # print('STRING this is the new id', push_status_dict.get('temp_id_mapping').get(str(uuid)))
                        # print('STRING this is the new id', push_status_dict.get('temp_id_mapping').get(uuid))
                        # task['task_tm_link_id'] = push_status_dict.get('temp_id_mapping').get(uuid)
                        task['task_tm_link_id'] = push_status_dict.get('temp_id_mapping').get(task.get('task_tm_link_id'))
                        print('tsak ne')
                        print(task['task_tm_link_id'])
                    # convert task
                    task_notes_processed.append(process_batched_nm_task_to_nm_task(nm_task))
            # push processed todos to note manager
            push_task_to_nm(task_notes_processed, note)
            all_tasks_processed.append(task_notes_processed)

            batched_task_for_tm = {} #reset batched task
    else:
        raise Exception('Invalid sync_type given for sync_task_to_tm function, that pushes notes to todos.')

    return all_tasks_processed

def determine_task_change_status(nm_task:dict, current_run_time: object, tm_tasks:dict) -> str:
    """
    Determines change status in regards to the todo manager.

    Returns:
    - Returns a status string that defines its future sync status
        - new - does not exists in todo manager
        - open - exists in todo manager.
        - delete - task to be removed from todoist
        - ignore-* - will not be pushed to todo manager for various reasons stored in status
    """
    task_id = nm_task.get('task_tm_link_id')
    task_checkbox_status = nm_task['task_checkbox_status']
    task_recurrence = nm_task['task_recurrence']
    
    # do not process anything to todist if the task has no reason to be pushed 
    # 1st main reasons - closed already, ignoreable, cancelled from being worked on
    # 2nd main reason - the task is a completed recurrence task
    if (task_checkbox_status in ('close', 'ignore', 'cancel') and not task_id) or \
        (task_recurrence and task_checkbox_status == 'close'):
        nm_task['task_tm_status'] = 'ignore:by_checkbox_status_and_no_tm_id/recurrence'
        return 'ignore:by_checkbox_status/no_tm_id'
    
    # determine the date of the file and ignore based on recentness of file
    sync_types = sync_logic.get('sync_types')
    if sync_types:
        file_date = datetime.fromtimestamp(nm_task.get('task_file_mtime'))
        try:
            frontmatter_date = nm_task.get('task_frontmatter_properties').get(frontmatter_modified_date_field)
            frontmatter_date = re.search(frontmatter_modified_date_regex, frontmatter_date).group(0)
            frontmatter_date = datetime.strptime(frontmatter_date, "%Y-%m-%d")
        except:
            frontmatter_date = None
            
        sync_period = sync_logic.get('sync_period')
        comparison_date = None
        for sync_type in reversed(sync_types):
            if sync_type == 'file':
                comparison_date = file_date
            if sync_type == 'frontmatter':
                comparison_date = frontmatter_date if frontmatter_date else comparison_date
        
        # compare the comparisson date if there is one to apply selective file date sync
        lookback_period = current_run_time - timedelta(minutes = sync_period)
        if comparison_date and comparison_date < lookback_period:
            nm_task['task_tm_status'] = 'ignore:by_modified_time'
            return 'ignore:by_modified_time'

    # Determine task_tm_sync_status for task that have a todo manager id already
    try:
        api_task = tm_tasks.get(task_id)
    except:
        if nm_task.get('task_tm_link_id'):
            api_task = nm_task
        else:
            api_task = None
    if api_task:
        # assume that if there is a todo manager task or a todo manager id in the task, then it had existed in todo manager
        # and is now completed if it is not in the active task list
        if api_task.get('is_completed', True) == True and task_checkbox_status in ('close', 'ignore', 'cancel'):
            nm_task['task_tm_status'] = 'ignore:by_complete_in_tm'
        elif api_task.get('is_completed', True) == False and task_checkbox_status in ('cancel', 'delete'):
            nm_task['task_tm_status'] = 'delete'
        elif api_task.get('is_completed', True) == False and task_checkbox_status in ('close'):
            nm_task['task_tm_status'] = 'close'
        else:
            nm_task['task_tm_status'] = 'open'
    elif task_checkbox_status in ('close', 'ignore', 'cancel'):
        # these should have been ignored earlier in function, therefore are errors
        nm_task['task_tm_status'] = 'error'
    else:
        nm_task['task_tm_status'] = 'new' #special status for sync. Need to create this task.

    return nm_task['task_tm_status']

def push_task_to_todoist(nm_task:dict, tm_sync_type:str) -> dict:
    """
    Takes a note manager task and applies the correct update to the todo manager for it

    Returns 
    - Dict of task that have been processed in the todo manager. Each task contains 
    information from the todo_manager and note manager for further processing.
    """

    # process the note manager task
    if tm_sync_type == 'rest':
        if 'ignore' in nm_task['task_tm_status']: 
            # if completed on both ends. This task is presumably old and should not be submitting further api calls.
            submitted_task = nm_task
            submitted_task['task_sync_status'] = 'ignored'
        elif nm_task['task_tm_status'] == 'new':
            submitted_task = create_new_task(nm_task)
            submitted_task['task_sync_status'] = 'created'
        elif nm_task['task_tm_status'] == 'open':
            submitted_task = update_existing_task(nm_task)
            submitted_task['task_sync_status'] = 'updated'
        elif nm_task['task_tm_status'] == 'close':
            submitted_task = complete_existing_task(nm_task)
            submitted_task['task_sync_status'] = 'completed'
        else:
            submitted_task = nm_task
            submitted_task['task_sync_status'] = 'error'
    else:
        if 'ignore' in nm_task['task_tm_status']: 
            nm_task['task_sync_status'] = 'ignored'
            submitted_task = None
        else:
            submitted_task = process_task_for_batch(nm_task)
    
    return submitted_task

def create_new_task(nm_task:dict, tm_sync_type:str) -> dict:
    """
    Creates the task in the todo manager

    Returns: 
    - A task submitted to the todo manger,
        converted back to a note_manager task with additional information
        from the todo manager.
    """

    td_nm_task = add_task_to_todoist(nm_task, tm_sync_type)
    return td_nm_task

def update_existing_task(nm_task: dict, tm_sync_type:str)-> dict:
    """
    Updates an existing task in the todo manager.

    Returns: 
    - A task submitted and update in the todo manger,
        converted back to a note_manager task with additional information
        from the todo manager.
    """
    td_nm_task = update_task_to_todoist(nm_task, tm_sync_type)
    return td_nm_task

def complete_existing_task(td_nm_task:dict, tm_sync_type:str) -> dict:
    """
    Updates the completion status.
    """
    td_nm_task = complete_task_to_todoist(td_nm_task)
    return td_nm_task

def create_reminder(nm_task:dict, tm_sync_type:str) -> dict:
    pass
    return None

def process_task_for_batch(nm_task):
    tm_task_proxy = process_task_for_submission_to_tm(nm_task)
    task_uuid = uuid.uuid4()
    print('task_uuid:', task_uuid)
    task_temp_uuid = uuid.uuid4()
    print('task_temp_uuid:', task_temp_uuid)
    task_tm_status = nm_task.get('task_tm_status')
    batch_task = None
    match task_tm_status:
        case 'new':
            task_sync_type = 'item_add'
            batch_task = {
                "type": f"{task_sync_type}",
                "temp_id": f"{task_temp_uuid}",
                "uuid": f"{task_uuid}",
                "args": tm_task_proxy,
            }
            # store task temp_id to be replaced later
            nm_task['task_tm_link_id'] = str(task_temp_uuid)
        case 'open':
            task_sync_type = 'item_update'
            batch_task = {
                "type": f"{task_sync_type}",
                "uuid": f"{task_uuid}",
                "args": tm_task_proxy,
        }
        case 'close':
            task_sync_type = 'item_complete'
            batch_task = {
                "type": f"{task_sync_type}",
                "uuid": f"{task_uuid}",
                "args": {'ids': [str(nm_task.get('task_tm_link_id'))]},
        }
        case 'delete':
            task_sync_type = 'item_delete'
            batch_task = {
                "type": f"{task_sync_type}",
                "uuid": f"{task_uuid}",
                "args": {'ids': [str(nm_task.get('task_tm_link_id'))]},
        }
            
    batched_task_for_tm[str(task_uuid)] = nm_task
    return batch_task