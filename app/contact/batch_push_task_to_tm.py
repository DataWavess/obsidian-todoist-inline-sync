import os
import json
import uuid
from variables import app_location
from contact.tm_api import push_batched_commands
from writeback.push_task_to_nm import push_task_to_nm
from convert.task_converters import process_batch_task_for_submission_to_tm, process_batched_nm_task_to_nm_task
from contact.determine_task_status import determine_task_change_status

batched_task_for_tm = {}
batched_reminder_for_tm = {}
batched_sub_task_movement_for_tm = {}
batched_project_movement_for_tm = {}
all_nm_tasks_keys = {}
tm_projects = {}

def batch_sync_task_to_tm(nm_notes:dict, nm_tasks_keys: dict, current_run_time:object, sync_logic: object) -> dict:
    """
    Processes a list of notes, extracting associated tasks from a dictionary, 
    and then submits these tasks to the note manager with the appropriate context."

    Parameters:
    - A full list of notes contained in a vault and their associated task.
    
    Returns:
    - None
    """
    global batched_task_for_tm
    global all_nm_tasks_keys
    global tm_projects
    all_nm_tasks_keys = nm_tasks_keys
    all_synced_task = []
    all_failed_synced_task = []
    # read in todo manager for status determination
    with open(os.path.join(app_location, 'tm_tasks.json'), 'r') as f:
        tm_tasks = json.load(f)
    
    # open tasks list
    with open(os.path.join(app_location, 'projects.json'), 'r', encoding='utf-8') as f:
        tm_projects = json.load(f)
    
    # process task in each note
    for note in nm_notes:
        task_notes_synced = []
        batched_tasks = []
        task_notes_ignored = []
        # process task in current note
        for nm_task in nm_notes[note]:
            determine_task_change_status(nm_task, current_run_time, tm_tasks, sync_logic)
            prepared_batch_task = batch_task_for_todoist(nm_task)
            if prepared_batch_task:
                for command in prepared_batch_task:
                    batched_tasks.append(command)
            else:
                task_notes_ignored.append(nm_task)

        # push batched task to todo manager
        for i in range(0, len(batched_tasks), 100):
            upload_batch = batched_tasks[i:i+100]
            push_status_dict = push_batched_commands(upload_batch)
            sync_status_dict = push_status_dict.get('sync_status')
            # update task with its pushed status from status dict returned by todo manager
            for uuid, uuid_status in sync_status_dict.items():
                attached_task_from_sync = batched_task_for_tm.get(uuid)
                # if current batch item is a task add it to be written
                if attached_task_from_sync:
                    attached_task_from_sync['task_batch_synced_status'] = uuid_status
                    # save new tm_id if created the task
                    if attached_task_from_sync['task_tm_status'] == 'new' and uuid_status == 'ok':
                        attached_task_from_sync['task_tm_link_id'] = push_status_dict.get('temp_id_mapping').get(attached_task_from_sync.get('task_sync_temp_tm_link_id'))
                    
                    # apply a reminder status if applicable to creation and is valid
                    if batched_reminder_for_tm.get(uuid):
                        if sync_status_dict.get(batched_reminder_for_tm.get(uuid).get('uuid')) == 'ok':
                            attached_task_from_sync['task_reminder_notification_exists'] = True
                        else:
                            # store failed reminders
                            batched_reminder_for_tm.get(uuid)['command_type'] = 'create reminder'
                            attached_task_from_sync['task_reminder_batch_synced_status'] = batched_reminder_for_tm.get(uuid)

                    # if there are failures to moving a task/sub_task relationship, add it to log file
                    if batched_sub_task_movement_for_tm.get(uuid):
                        if sync_status_dict.get(batched_sub_task_movement_for_tm.get(uuid).get('uuid')) != 'ok':
                            batched_sub_task_movement_for_tm.get(uuid)['failure_message'] = sync_status_dict.get(batched_sub_task_movement_for_tm.get(uuid).get('uuid'))
                            batched_sub_task_movement_for_tm.get(uuid)['command_type'] = 'change parent task'
                            attached_task_from_sync['task_reminder_batch_synced_status'] = batched_sub_task_movement_for_tm.get(uuid)
                    
                    # if there are failures to moving a project relationship, add it to log file
                    if batched_project_movement_for_tm.get(uuid):
                        if sync_status_dict.get(batched_project_movement_for_tm.get(uuid).get('uuid')) != 'ok':
                            batched_project_movement_for_tm.get(uuid)['failure_message'] = sync_status_dict.get(batched_project_movement_for_tm.get(uuid).get('uuid'))
                            batched_project_movement_for_tm.get(uuid)['command_type'] = 'change project'
                            attached_task_from_sync['task_reminder_batch_synced_status'] = batched_project_movement_for_tm.get(uuid)
                    
                    # store task to be pushed to the note
                    converted_nm_task = process_batched_nm_task_to_nm_task(attached_task_from_sync)
                    if uuid_status == 'ok':
                        # convert task
                        task_notes_synced.append(converted_nm_task)
                    else:
                        all_failed_synced_task.append(converted_nm_task)

        # push processed todos to note manager
        if task_notes_synced:
            push_task_to_nm(task_notes_synced, note)
            all_synced_task.extend(task for task in task_notes_synced)

        batched_task_for_tm = {} # reset batched task for next note to process
    
    # save failed task file
    with open(os.path.join(app_location, 'failed_sync_task.json'), 'w') as f:
        json.dump(all_failed_synced_task, f)
    # open the failed sync task file if there are any
    if all_failed_synced_task:
        failed_file_path = os.path.join(app_location, 'failed_sync_task.json')
        try:
            os.system(fr'code "{failed_file_path}"')
        except:
            pass
        
    return all_synced_task

def batch_task_for_todoist(nm_task:dict) -> dict:
    """
    Takes a note manager task and applies the correct update to the todo manager for it

    Returns 
    - Dict of task that have been processed in the todo manager. Each task contains 
    information from the todo_manager and note manager for further processing.
    """    

    if 'ignore' in nm_task['task_tm_status']:
        nm_task['task_sync_status'] = 'ignored'
        submitted_task = []
    else:
        submitted_task = process_task_for_batch(nm_task)
    
    return submitted_task

def process_task_for_batch(nm_task: dict) -> list:
    tm_task_proxy = process_batch_task_for_submission_to_tm(nm_task)
    task_uuid = uuid.uuid4()
    task_temp_uuid = uuid.uuid4()
    task_tm_status = nm_task.get('task_tm_status')
    prepared_batch = []
    print(nm_task.get('task_key'), task_tm_status)
    
    # create task movement commands regarding project movement
    if nm_task['task_tm_link_id'] \
        and nm_task['task_tm_project_path_name'] != nm_task['task_tm_associated_project_name']:
        if task_tm_status in ('open', 'close', 'delete'):
            project_uuid = str(uuid.uuid4())
            project_id = tm_projects.get('name_based').get(nm_task['task_tm_project_path_name'], {}).get('id')
            batch_task_project = {
                "type": "item_move",
                "uuid": project_uuid,
                "args": {
                    "id": nm_task['task_tm_link_id'],
                    "project_id": project_id,
                }
            }
            prepared_batch.append(batch_task_project)
            batched_project_movement_for_tm[str(task_uuid)] = batch_task_project

    # create task movement commands regarding a sub task and its parent task
    parent_key = nm_task['task_group_parent_key']
    # pull the parent id from the existing tm_parent_id or from the newly created temp_uuid in place of its existing key
    parent_id = all_nm_tasks_keys.get(parent_key, {}).get('task_tm_link_id') or all_nm_tasks_keys.get(parent_key, {}).get('task_sync_temp_tm_link_id')

    if task_tm_status in ('new'):
        tm_task_proxy['parent_id'] = parent_id
    elif task_tm_status in ('open', 'close', 'delete'):
        sub_task_uuid = str(uuid.uuid4())
        nm_parent_id = all_nm_tasks_keys.get(parent_key, {}).get('task_tm_link_id')
        tm_parent_id = nm_task['task_tm_associated_parent_id']
        if nm_parent_id != tm_parent_id:
            batch_task_sub = {
                "type": "item_move",
                "uuid": sub_task_uuid,
                "args": {
                    "id": nm_task['task_tm_link_id'],
                    "parent_id": parent_id,
                }
            }
            if nm_parent_id is None: # turning it into a main task
                del batch_task_sub['args']['parent_id']
                batch_task_sub['args']['project_id'] = tm_task_proxy['project_id']
            
            prepared_batch.append(batch_task_sub)
            batched_sub_task_movement_for_tm[str(task_uuid)] = batch_task_sub

    # create main batch command for the task
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
            nm_task['task_sync_temp_tm_link_id'] = str(task_temp_uuid)
            all_nm_tasks_keys[nm_task['task_key']]['task_sync_temp_tm_link_id'] = str(task_temp_uuid)
        case 'open':
            task_sync_type = 'item_update'
            batch_task = {
                "type": f"{task_sync_type}",
                "uuid": f"{task_uuid}",
                "args": tm_task_proxy,
            }
        case 'close':
            task_sync_type = 'item_complete'
            args = {'id': str(nm_task.get('task_tm_link_id')) }
            args['date_completed'] = nm_task['task_dates'].get('completed_date')

            batch_task = {
                "type": f"{task_sync_type}",
                "uuid": f"{task_uuid}",
                "args": args,
            }
        case 'delete':
            task_sync_type = 'item_delete'
            args = {'id': str(nm_task.get('task_tm_link_id')) }
            batch_task = {
                "type": f"{task_sync_type}",
                "uuid": f"{task_uuid}",
                "args": args,
            }
            
    prepared_batch.append(batch_task)
    batched_task_for_tm[str(task_uuid)] = nm_task

    # add a reminder if the task has one un-submitted
    if (task_tm_status in ('new', 'open')) and (nm_task['task_dates'].get('reminder_date')) and (not nm_task['task_reminder_notification_exists']):
        task_sync_type = 'item_add'
        reminder_uuid = uuid.uuid4()
        reminder_temp_uuid = uuid.uuid4()
        reminder = {
            "item_id": f"{nm_task.get('task_tm_link_id') or str(task_temp_uuid)}",
            'due': {
                'date': nm_task['task_dates'].get('reminder_date'),
            },
            'type': 'absolute',
        }
        batch_task = {
            "type": f"reminder_add",
            "temp_id": f"{reminder_uuid}",
            "uuid": f"{reminder_temp_uuid}",
            "args": reminder,
        }
        prepared_batch.append(batch_task)
        batched_reminder_for_tm[str(task_uuid)] = batch_task
    
    return prepared_batch