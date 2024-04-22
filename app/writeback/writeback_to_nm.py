from writeback.push_task_to_nm import push_task_to_nm, push_new_task_to_nm, push_new_recurring_completion_task_to_nm
from convert.task_converters import convert_definitive_tm_task_to_nm, convert_tm_task_to_new_nm_task
from variables import inbox_location, app_location
import os
import copy
import json
from datetime import datetime

def writeback_since_sync_to_nm(tm_tasks, missing_recurring_completions, notes_nm_task, tm_project_beacons, tm_changes_since_last_sync=None):
    """
    Processes todo manager task and writes them to 
    note manager. Without knowing state of last updates from the note manager
    assumption is that this is run when everything from the note manager has been pushed to 
    the todo manager already. 
    """
    deleted_tm_tasks = []
    new_tm_task_ids = []
    new_items = {}

    # pull in task that have ever been completed
    with open(os.path.join(app_location, 'tm_tasks_closed_historically.json')) as f:
        try:
            closed_tasks_historical = json.load(f)
        except:
            closed_tasks_historical = {}

    notes_tm_task = {}
    # create a task dict of task based on their task_tm_link_id
    for note, nm_tasks in notes_nm_task.items():
        for nm_task in nm_tasks:
            task_tm_link_id = nm_task.get('task_tm_link_id')
            if task_tm_link_id and (task_tm_link_id not in notes_tm_task):
                notes_tm_task[task_tm_link_id] = nm_task
            # overwrite the task_id in the dict if the recurring task is not another closed task
            elif nm_task['task_recurrence'] and nm_task['task_checkbox_status'] != 'close':
                notes_tm_task[task_tm_link_id] = nm_task

    # iterate over task updates 
    updated_note_tasks = []
    created_recurring_completed_task = []
    new_tm_task_ids = []
    for tm_id, tm_activity in tm_changes_since_last_sync.items():
        nm_task = notes_tm_task.get(tm_id)
        # exists in notes
        if nm_task:
            original_nm_task = copy.deepcopy(nm_task)
            tm_task = tm_tasks.get(nm_task.get('task_tm_link_id'))
            # existing data
            if tm_activity.get('event_type') in ('updated', 'added', 'uncompleted'):
                nm_task['task_tm_writeback_status'] = 'exist'
                nm_task['task_tm_object'] = tm_task
                converted_task = convert_definitive_tm_task_to_nm(copy.deepcopy(tm_task), nm_task)
                updated_note_tasks.append(converted_task)
            # these next two activity types (completed, deleted) are essentially the final stage of a task.
            elif tm_activity.get('event_type') in ('completed') \
                and nm_task['task_recurrence'] is None:
                # task has been completed
                nm_task['task_checkbox'] = '[x]'
                nm_task['task_checkbox_next_symbol'] = 'x'
                nm_task['task_checkbox_status'] = 'close'
                try: 
                    tm_completed_date = datetime.strptime(closed_tasks_historical.get(tm_id).get('completed_at'), '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d')
                except:
                    pass
                nm_task['task_dates']['completed_date'] = nm_task['task_dates'].get('completed_date') or tm_completed_date
                updated_note_tasks.append(nm_task)
            elif tm_activity.get('event_type') in ('deleted'):
                # assumed the task has been deleted if not completed and does not exists in downloaded data from todo manager
                nm_task['task_checkbox'] = '[_]'
                nm_task['task_checkbox_next_symbol'] = '_'
                nm_task['task_checkbox_status'] = 'delete'
                nm_task['task_tm_writeback_status'] = 'deleted'
                nm_task['task_tm_object'] = None
                updated_note_tasks.append(nm_task)
                deleted_tm_tasks.append(nm_task)

            # create records for task that are the parent (open) and are missing completions from the todo manager
            # create recurrence records for existing task that are not in the note manager
            if nm_task.get('task_tm_link_id') in missing_recurring_completions and original_nm_task.get('task_checkbox_status') == 'open':
                tm_completions_to_create = missing_recurring_completions.get(original_nm_task.get('task_tm_link_id')).get('task_completions')
                tm_completions_to_create = set(tm_completions_to_create)
                for completion_date in tm_completions_to_create:
                    new_nm_task = original_nm_task
                    new_nm_task['task_recurrence_parent_md_line'] = original_nm_task['task_md_line']
                    new_nm_task['task_recurrence_parent_due_date'] = original_nm_task['task_dates'].get('due_date')
                    new_nm_task['task_recurrence_tm_active_due_date'] = missing_recurring_completions.get(original_nm_task.get('task_tm_link_id')).get('task_active_due_date')
                    new_nm_task['task_recurrence_completed_date'] = completion_date
                    new_nm_task['task_dates']['completed_date'] = completion_date
                    # update the copied open record settings to mark the completion record as closed
                    new_nm_task['task_checkbox'] = '[x]'
                    new_nm_task['task_checkbox_next_symbol'] = 'x'
                    new_nm_task['task_checkbox_status'] = 'close'
                    created_recurring_completed_task.append(new_nm_task)
        else:
            new_tm_task_ids.append(tm_id)
        
    # group the updated and created recurring task into dicts by their note as the key
    updated_task_by_note = {}
    for task in updated_note_tasks:
        note = task['task_file_location']
        if note in updated_task_by_note:
            updated_task_by_note[note].append(task)
        else:
            updated_task_by_note[note] = [task]
    
    new_recurring_task_by_note = {}
    for task in created_recurring_completed_task:
        note = task['task_file_location']
        if note in new_recurring_task_by_note:
            new_recurring_task_by_note[note].append(task)
        else:
            new_recurring_task_by_note[note] = [task]

    # Update the note page for any updates from todo manager
    for note, updated_note_tasks in updated_task_by_note.items():
        if updated_note_tasks:
            push_task_to_nm(updated_note_tasks, note)

    ## TODO: remove/move any deleted task from vault notes
    ## code...
    
    # Organize the new tm task for the beacon page they are to be placed in
    tm_new_task_for_beacon = {value: [] for key, value in tm_project_beacons.items()}
    tm_new_task_for_beacon[inbox_location] = [] # add the inbox page to the list of beacons

    for tm_task_id in new_tm_task_ids:
        tm_task = tm_tasks.get(tm_task_id)
        # only active task
        if tm_task: 
            note_location = tm_project_beacons.get(tm_task.get('project_id'))
            tm_task['task_tm_beacon_location'] = note_location if note_location else inbox_location
            tm_new_task_for_beacon[tm_task['task_tm_beacon_location']].append(tm_task)

    return tm_new_task_for_beacon, new_recurring_task_by_note


def writeback_new_task_lines_to_nm(tm_new_task_for_beacon, new_recurring_task_by_note):
    _writeback_new_recurring_completion_task_to_nm(new_recurring_task_by_note)
    _writeback_new_task_to_beacons(tm_new_task_for_beacon)
    return None

def _writeback_new_recurring_completion_task_to_nm(new_recurring_task_by_note):
    for note, tm_tasks in new_recurring_task_by_note.items():
        push_new_recurring_completion_task_to_nm(tm_tasks, note)
    return None

def _writeback_new_task_to_beacons(tm_new_task_for_beacon):
    # Place any new task from todo manager into their beacon pages
    for note, tm_tasks in tm_new_task_for_beacon.items():
        converted_tasks = []
        for tm_task in tm_tasks:
            converted_tasks.append(convert_tm_task_to_new_nm_task(tm_task))
        push_new_task_to_nm(converted_tasks, note)
    return None

def writeback_td_task_to_nm(tm_tasks, missing_recurring_completions, notes_nm_task, tm_project_beacons):
    """
    Processes todo manager task and writes them to 
    note manager. Without knowing state of last updates from the note manager
    assumption is that this is run when everything from the note manager has been pushed to 
    the todo manager already. 
    """
    deleted_tm_tasks = []
    existing_tm_task_in_nm_ids = []
    new_tm_task_ids = []

    # pull in task that have ever been completed
    with open(os.path.join(app_location, 'tm_tasks_closed_historically.json')) as f:
        try:
            closed_tasks_historical = json.load(f)
        except:
            closed_tasks_historical = {}

    # iterate over task in vault, apply status and add them to a respective list for 
    # further processing on updating a markdown file.
    for note, nm_tasks in notes_nm_task.items():
        updated_note_tasks = []
        created_recurring_completed_task = []
        # determine if any updates for a note
        for nm_task in nm_tasks:
            tm_id = nm_task['task_tm_link_id']
            # process over note manager task that are associated with todo manager task.
            if tm_id:
                existing_tm_task_in_nm_ids.append(tm_id)
                associated_tm_task = tm_tasks.get(tm_id)
                if associated_tm_task:
                    nm_task['task_tm_writeback_status'] = 'exist'
                    nm_task['task_tm_object'] = associated_tm_task
                    converted_task = convert_definitive_tm_task_to_nm(copy.deepcopy(associated_tm_task), nm_task)
                    updated_note_tasks.append(converted_task)
                    # if for whatever reason we can't get all the todo manager task. We should not update the ones that are handled. Most likely historic.
                elif nm_task['task_checkbox_status'] not in ('ignore', 'close', 'cancel', 'delete'): #TODO: determine if we should not use cancellations deletions. Ignore and close are fine.
                    if closed_tasks_historical.get(tm_id) and not nm_task.get('task_recurrence'):
                        # task has been completed
                        nm_task['task_checkbox'] = '[x]'
                        nm_task['task_checkbox_next_symbol'] = 'x'
                        nm_task['task_checkbox_status'] = 'close'
                        tm_completed_date = datetime.strptime(closed_tasks_historical.get(tm_id).get('completed_at'), '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d')
                        nm_task['task_dates']['completed_date'] = nm_task['task_dates'].get('completed_date') or tm_completed_date
                        updated_note_tasks.append(nm_task)
                    else:
                        # assumed the task has been deleted if not completed and does not exists in downloaded data from todo manager
                        nm_task['task_checkbox'] = '[_]'
                        nm_task['task_checkbox_next_symbol'] = '_'
                        nm_task['task_checkbox_status'] = 'delete'
                        nm_task['task_tm_writeback_status'] = 'deleted'
                        nm_task['task_tm_object'] = None
                        # deprecated - no needt to convert
                        # converted_task = convert_definitive_tm_task_to_nm(associated_tm_task, nm_task)
                        updated_note_tasks.append(nm_task)
                        deleted_tm_tasks.append(nm_task)
                    
                # create records for task that are the parent (open) and are missing completions from the todo manager
                # create recurrence records for existing task that are not in the note manager
                if nm_task.get('task_tm_link_id') in missing_recurring_completions and nm_task.get('task_checkbox_status') == 'open':
                    tm_completions_to_create = missing_recurring_completions.get(nm_task.get('task_tm_link_id')).get('task_completions')
                    for completion in tm_completions_to_create:
                        new_nm_task = copy.deepcopy(nm_task)
                        new_nm_task['task_recurrence_parent_md_line'] = nm_task['task_md_line']
                        new_nm_task['task_recurrence_parent_due_date'] = nm_task['task_dates'].get('due_date')
                        new_nm_task['task_recurrence_tm_active_due_date'] = missing_recurring_completions.get(nm_task.get('task_tm_link_id')).get('task_active_due_date')
                        new_nm_task['task_recurrence_completed_date'] = completion
                        new_nm_task['task_dates']['completed_date'] = completion
                        # update the copied open record settings to mark the completion record as closed
                        new_nm_task['task_checkbox'] = '[x]'
                        new_nm_task['task_checkbox_next_symbol'] = 'x'
                        new_nm_task['task_checkbox_status'] = 'close'
                        created_recurring_completed_task.append(new_nm_task)
            else:
                nm_task['task_tm_writeback_status'] = None
        
        # Update the note page for any updates from todo manager
        if updated_note_tasks:
            push_task_to_nm(updated_note_tasks, note)
            push_new_recurring_completion_task_to_nm(created_recurring_completed_task, note)

    ## TODO: remove/move any deleted task from vault notes
    # Check for any new task in todoist
    all_tm_tasks = [tm_id for tm_id in tm_tasks.keys()]
    new_tm_task_ids = [tm_id for tm_id in all_tm_tasks if tm_id not in existing_tm_task_in_nm_ids]
    
    # Organize the new tm task for the beacon page they are to be placed in
    tm_new_task_for_beacon = {value: [] for key, value in tm_project_beacons.items()}
    tm_new_task_for_beacon[inbox_location] = [] # add the inbox page to the list of beacons

    for tm_task_id in new_tm_task_ids:
        tm_task = tm_tasks.get(tm_task_id)
        note_location = tm_project_beacons.get(tm_task.get('project_id'))
        tm_task['task_tm_beacon_location'] = note_location if note_location else inbox_location
        tm_new_task_for_beacon[tm_task['task_tm_beacon_location']].append(tm_task)
    
    # Place any new task from todo manager into their beacon pages
    for note, tm_tasks in tm_new_task_for_beacon.items():
        converted_tasks = []
        for tm_task in tm_tasks:
            converted_tasks.append(convert_tm_task_to_new_nm_task(tm_task))
        push_new_task_to_nm(converted_tasks, note)
    
            
    return None

