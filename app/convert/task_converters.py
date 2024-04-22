from variables import td_todo_tags, td_todo_prefix, user_add_created_date_to_all_task_without_it
from read.parse_projects import get_tm_project
import urllib.parse
import re
from datetime import datetime


def process_batched_nm_task_to_nm_task(nm_task: dict) -> dict:
    """
    Lints nm_task for rewriting to note manager
    Returns:
    - A task labeled with fields that are to be accepted by todo manager
    """
    # get the link address
    pattern = r'\[Obsidian Link\]\(obsidian://open\?vault=[^&]+&file=[^\)]+\)'
    matches = re.findall(pattern, nm_task['description'])
    # Extract the first match if there is one
    if matches:
        obsidian_link = matches[0]
    else:
        obsidian_link = None

    # add completion date
    if nm_task['task_checkbox_status_type'] == 'done':
        nm_task['task_dates']['completed_date'] = nm_task['task_dates'].get('completed_date') or datetime.now().strftime('%Y-%m-%d')
    
    # add created date if user setting allows
    if user_add_created_date_to_all_task_without_it:
        nm_task['task_dates']['created_date'] = nm_task['task_dates'].get('created_date') or datetime.now().strftime('%Y-%m-%d')

    # new fields to add
    # nm_task['task_has_pushed_reminder'] #TODO: add icon here i think
    # nm_task['task_checkbox'] = '[x]' if nm_task['task_is_completed'] else nm_task['task_checkbox'] #TODO: determine if this is needed. Should already be up to date in task manager.
    nm_task['task_nm_link'] = obsidian_link
    if nm_task['task_tm_link_id']:
        nm_task['task_tm_link'] = '[Todoist]' + '(https://todoist.com/showTask?id=' + str(nm_task.get('task_tm_link_id')) + ')'
    # nm_task['task_tm_link_id'] = nm_task.get('task_tm_link_id')
    
    # Apply hash tags to labels
    nm_task['task_labels'] = list(set(nm_task['task_labels']))
    for count, tag in enumerate(nm_task['task_labels']):
        if tag.replace('#', '') in td_todo_tags:
            tag = f'#{td_todo_prefix}/' + tag.replace('#', '')
        else:
            tag = '#' + tag.replace('#', '')
        nm_task['task_labels'][count] = tag
    
    return nm_task

def convert_tm_to_nm_task(tm_task: dict, nm_task: dict) -> dict:
    """
    Receives a task from todoist and converts to a format
     the note manager can accept.
    Returns:
    - A task labeled with fields that are to be accepted by todo manager
    """
    # get the link address
    pattern = r'\[Obsidian Link\]\(obsidian://open\?vault=[^&]+&file=[^\)]+\)'
    matches = re.findall(pattern, tm_task['description'])
    # Extract the first match if there is one
    if matches:
        obsidian_link = matches[0]
    else:
        obsidian_link = None

    # create the task dict for the note manager.
    tm_nm_task = {
        'task_dates': {
            'due_date': tm_task.get('due').get('date') if tm_task['due'] else None
        },
        'task_recurrence': tm_task.get('due').get('string') if tm_task['due'] and tm_task.get('due').get('is_recurring') else None,
        'task_labels': tm_task['labels'],
        'task_checkbox': '[x]'  if tm_task['is_completed'] else nm_task['task_checkbox'],
        'task_checkbox_status': nm_task['task_checkbox_status'],
        'task_name': tm_task['content'],
        'task_priority': tm_task['priority'],
        'task_nm_link': obsidian_link,
        'task_tm_link': '[Todoist]' + '(https://todoist.com/showTask?id=' + str(tm_task['id']) + ')',
        'task_tm_link_id': nm_task.get('task_tm_link_id'),
    }

    # Apply hash tags to labels
    nm_task['task_labels'] = list(set(nm_task['task_labels']))
    for count, tag in enumerate(tm_nm_task['task_labels']):
        if tag in td_todo_tags:
            tag = f'#{td_todo_prefix}/' + tag
        else:
            tag = '#' + tag
        tm_nm_task['task_labels'][count] = tag

    # convert priority 
    todoist_value_mapping = {4: 'p1', 3: 'p2', 2: 'p3', 1:'p4'}
    tm_nm_task['task_priority'] = todoist_value_mapping.get(tm_nm_task.get('task_priority'), nm_task.get('task_priority'))

    fields_to_place_back_in_task_object = ['task_file_location', 'task_file_name', 'task_md_line', 'task_checkbox_prefix', 'task_checkbox', 'task_dates', 'task_level']
    for field in fields_to_place_back_in_task_object:
        tm_nm_task[field] = nm_task[field]
    return tm_nm_task


def convert_definitive_tm_task_to_nm(tm_task: dict, nm_task: dict) -> dict:
    """
    Receives a task from todoist and converts to a format
     the note manager can accept. Source of truth is placed on the todo manager.
    Returns:
    - A task labeled with fields that are to be accepted by todo manager
    """
    # get the link address
    pattern = r'\[Obsidian Link\]\(obsidian://open\?vault=[^&]+&file=[^\)]+\)'
    matches = re.findall(pattern, tm_task['description'])
    # Extract the first match if there is one
    if matches:
        obsidian_link = matches[0]
    else:
        obsidian_link = None

    # create the task dict for the note manager.
    tm_nm_task = {
        'task_dates': {
            'due_date': tm_task.get('due').get('date') if tm_task['due'] else None
        },
        'task_recurrence': tm_task.get('due').get('string') if tm_task['due'] and tm_task.get('due').get('is_recurring') else None,
        'task_labels': tm_task['labels'],
        'task_checkbox': '[x]' if tm_task['is_completed'] else nm_task['task_checkbox'],
        'task_checkbox_status': 'done' if tm_task['is_completed'] else nm_task['task_checkbox_status'],
        'task_name': tm_task['content'],
        'task_priority': tm_task['priority'],
        'task_nm_link': obsidian_link,
        'task_tm_link': '[Todoist]' + '(https://todoist.com/showTask?id=' + str(tm_task['id']) + ')',
        'task_tm_link_id': tm_task['id'],
        'task_parent_id': tm_task['parent_id'],
        'task_reminder_notification_exists': nm_task['task_reminder_notification_exists'],
    }

    # update recurrence to match note manager
    if tm_nm_task['task_recurrence']:
        if 'every!' in tm_nm_task['task_recurrence']:
            tm_nm_task['task_recurrence'] = tm_nm_task['task_recurrence'].replace('every!', 'every')
            tm_nm_task['task_recurrence'] = tm_nm_task['task_recurrence'].strip() + ' when done'
            tm_nm_task['task_labels'].append('repeat_chore')
        else:
            tm_nm_task['task_labels'].append('repeat_duty')
        

    # Apply hash tags to labels
    tm_nm_task['task_labels'] = list(set(tm_nm_task['task_labels']))
    for count, tag in enumerate(tm_nm_task['task_labels']):
        if tag in td_todo_tags:
            tag = f'#{td_todo_prefix}/' + tag
        else:
            tag = '#' + tag
        tm_nm_task['task_labels'][count] = tag

    # Apply deleted hashtag 
    if nm_task['task_tm_writeback_status'] == 'deleted':
        tm_nm_task['task_labels'].append(f'#{td_todo_prefix}/deleted')

    # convert priority
    todoist_value_mapping = {4: 'p1', 3: 'p2', 2: 'p3', 1:'p4'}
    tm_nm_task['task_priority'] = todoist_value_mapping.get(tm_nm_task.get('task_priority'), nm_task.get('task_priority'))

    fields_to_place_back_in_task_object = ['task_file_location', 'task_file_name', 'task_md_line', 'task_checkbox_prefix', 'task_level']
    for field in fields_to_place_back_in_task_object:
        tm_nm_task[field] = nm_task[field]

    # update the dates in the object from note manager if there are any missing in the todo manger object
    has_due_like_date = False
    for date_type, date_value in nm_task.get('task_dates').items():
        if date_type in ('scheduled_date', 'start_date'):
            has_due_like_date = True
        if date_type not in tm_nm_task.get('task_dates'):
            tm_nm_task['task_dates'][date_type] = date_value
    # remove due date if there is due_date_like date in the todo manager already 
    # would mean that the date is created from one of those dates already
    if has_due_like_date and 'due_date' not in nm_task.get('task_dates').keys():
        del tm_nm_task['task_dates']['due_date']
    if tm_nm_task['task_dates'].get('due_date','') is None:
        del tm_nm_task['task_dates']['due_date']


    return tm_nm_task


def convert_tm_task_to_new_nm_task(tm_task: dict) -> dict:
    """
    Receives a task from todoist and converts to a format
     the note manager can accept. Source of truth is placed on the todo manager.
    Returns:
    - A task labeled with fields that are to be accepted by todo manager
    """
    # get the link address
    pattern = r'\[Obsidian Link\]\(obsidian://open\?vault=[^&]+&file=[^\)]+\)'
    matches = re.findall(pattern, tm_task['description'])
    # Extract the first match if there is one
    if matches:
        obsidian_link = matches[0]
    else:
        obsidian_link = None

    # create the task dict for the note manager.
    tm_nm_task = {
        'task_dates': {
            'due_date': tm_task.get('due').get('date') if tm_task['due'] else None,
            'created_date': datetime.strptime(tm_task['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime('%Y-%m-%d'),
        },
        'task_recurrence': tm_task.get('due').get('string') if tm_task['due'] and tm_task.get('due').get('is_recurring') else None,
        'task_labels': tm_task['labels'],
        'task_checkbox': '[x]' if tm_task['is_completed'] else '[ ]',
        'task_checkbox_status': 'done' if tm_task['is_completed'] else 'open',
        'task_name': tm_task['content'],
        'task_priority': tm_task['priority'],
        'task_nm_link': obsidian_link,
        'task_tm_link': '[Todoist]' + '(https://todoist.com/showTask?id=' + str(tm_task['id']) + ')',
        'task_tm_link_id': tm_task['id'],
        'task_parent_id': tm_task['parent_id'],
    }

    # Apply hash tags to labels
    tm_nm_task['task_labels'] = list(set(tm_nm_task['task_labels']))
    for count, tag in enumerate(tm_nm_task['task_labels']):
        if tag in td_todo_tags:
            tag = f'#{td_todo_prefix}/' + tag
        else:
            tag = '#' + tag
        tm_nm_task['task_labels'][count] = tag

    # convert priority 
    todoist_value_mapping = {4: 'p1', 3: 'p2', 2: 'p3', 1:'p4'}
    tm_nm_task['task_priority'] = todoist_value_mapping.get(tm_nm_task.get('task_priority'), None)

    # fields_to_place_back_in_task_object = ['task_file_location', 'task_file_name', 'task_md_line', 'task_checkbox_prefix', 'task_checkbox', 'task_dates', 'task_level']
    # for field in fields_to_place_back_in_task_object:
    #     tm_nm_task[field] = nm_task[field]
    return tm_nm_task



def convert_nm_task_tm_task(nm_task: dict) -> dict:
    """
    Converts a note manager task to a task in the format of the note manager's
    required API.

    Returns: 
    - A converted td_task = td_nm_task
    """
    td_nm_task = process_task_for_submission_to_tm(nm_task)
    return td_nm_task


def process_batch_task_for_submission_to_tm(nm_task: dict) -> dict:
    # Add link back to note manager for task
    nm_task['task_nm_link'] = '[Obsidian](obsidian://open?vault=' + urllib.parse.quote(nm_task.get('task_file_location').split('\\')[0]) + '&file=' + urllib.parse.quote(''.join(nm_task.get('task_file_location').split('\\')[1:])) + ')'
    tm_id = nm_task.get('task_tm_link_id')
    if tm_id:
        nm_task['id'] = tm_id
    
    nm_task['content'] = nm_task['task_name']
    nm_task['description'] = nm_task['task_nm_link']
    
    # Get the project id to add the task to
    nm_task['project_id'] = get_tm_project(nm_task)

    # convert priority 
    todoist_value_mapping = {'p1': 4, 'p2': 3, 'p3': 2, 'p4': 1}
    nm_task['priority'] = todoist_value_mapping.get(nm_task.get('task_priority'), None)
    if not nm_task['priority']:
        nm_task['priority'] = 1 # if no priority set it to none. To ensure it gets overwritten 

    # struture a due date string and handle recurring task
    due_dates = {}
    if nm_task.get('task_recurrence'):
        task_due_dates = nm_task['task_dates']
        due_dates['date'] = task_due_dates.get('due_date', task_due_dates.get('scheduled_date', task_due_dates.get('start_date')))
        due_dates['string'] = nm_task.get('task_recurrence').strip()
        if 'when done' in nm_task.get('task_recurrence'): # this is a repeat based on completion date (chore)
            due_dates['string'] = due_dates['string'].replace('every', 'every!').replace('when done', '').strip()
            nm_task['task_labels'].append(f'#{td_todo_prefix}/repeat_chore')
            nm_task['task_labels'] = [label for label in nm_task['task_labels'] if f'#{td_todo_prefix}/repeat_duty' not in label]
        else:
            nm_task['task_labels'].append(f'#{td_todo_prefix}/repeat_duty')
            nm_task['task_labels'] = [label for label in nm_task['task_labels'] if f'#{td_todo_prefix}/repeat_chore' not in label]
        # DEPRECATED: would rather have duty vs chore instead of general repeat
        # if not any('repeat' in label for label in nm_task['task_labels']):
        #     nm_task['task_labels'].append('#repeat')
    else:
        task_due_dates = nm_task['task_dates']
        due_dates['date'] = task_due_dates.get('due_date', task_due_dates.get('scheduled_date', task_due_dates.get('start_date')))
        nm_task['task_labels'] = [label for label in nm_task['task_labels'] if f'#{td_todo_prefix}/repeat-' not in label]
                
    nm_task['due'] = due_dates

    # remove beginning hash tags from obsidian tag to submit to tags for todoist labels
    nm_task['task_labels'] = list(set(nm_task['task_labels']))
    nm_task['labels'] = []
    for tag in nm_task['task_labels']:
        if tag.startswith('#'):
            tag = tag[1:]
            nm_task['labels'].append(tag)

    # Remove the td_todo_prefix/ part of a tag
    for count, tag in enumerate(nm_task['labels']):
        removed_prefix_tag = tag.replace(f'{td_todo_prefix}/', '')
        if removed_prefix_tag in td_todo_tags:
            tag = removed_prefix_tag
        nm_task['labels'][count] = tag

    # Apply the required fields for the task
    tm_task = {key: value for key, value in nm_task.items() if not key.startswith('task_')}

    # print this
    # print('to be submitted:')
    # print(tm_task)
    # print()

    return tm_task


def process_task_for_submission_to_tm(nm_task: dict) -> dict:
    # Add link back to note manager for task
    nm_task['task_nm_link'] = '[Obsidian](obsidian://open?vault=' + urllib.parse.quote(nm_task.get('task_file_location').split('\\')[0]) + '&file=' + urllib.parse.quote(''.join(nm_task.get('task_file_location').split('\\')[1:])) + ')'
    tm_id = nm_task.get('task_tm_link_id')
    if tm_id:
        nm_task['id'] = tm_id
    
    nm_task['content'] = nm_task['task_name']
    nm_task['description'] = nm_task['task_nm_link']
    
    # Get the project id to add the task to
    nm_task['project_id'] = get_tm_project(nm_task)

    # convert priority 
    todoist_value_mapping = {'p1': 4, 'p2': 3, 'p3': 2, 'p4': 1}
    nm_task['priority'] = todoist_value_mapping.get(nm_task.get('task_priority'), None)
    if not nm_task['priority']:
        nm_task['priority'] = 1 # if no priority set it to none. To ensure it gets overwritten 

    # struture a due date string and handle recurring task
    if nm_task.get('task_recurrence'):
        task_due_dates = nm_task['task_dates']
        nm_task['due_date'] = task_due_dates.get('due_date', task_due_dates.get('scheduled_date', task_due_dates.get('start_date')))
        # nm_task['due_string'] = nm_task['due_date'] + ' ' + nm_task.get('task_recurrence').strip()
        nm_task['due_string'] =  nm_task.get('task_recurrence').strip()
        if not '#repeat' in nm_task['task_labels']:
            nm_task['task_labels'].append('#repeat')
    else:
        task_due_dates = nm_task['task_dates']
        nm_task['due_date'] = task_due_dates.get('due_date', task_due_dates.get('scheduled_date', task_due_dates.get('start_date')))
        if '#repeat' in nm_task['task_labels']:
            nm_task['task_labels'].remove('#repeat')

    # remove beginning hash tags from obsidian tag to submit to tags for todoist labels
    nm_task['labels'] = []
    for tag in nm_task['task_labels']:
        if tag.startswith('#'):
            tag = tag[1:]
            nm_task['labels'].append(tag)

    # Remove the td_todo_prefix/ part of a tag
    for count, tag in enumerate(nm_task['labels']):
        removed_prefix_tag = tag.replace(f'{td_todo_prefix}/', '')
        if removed_prefix_tag in td_todo_tags:
            tag = removed_prefix_tag
        nm_task['labels'][count] = tag

    # Apply the required fields for the task
    tm_task = {key: value for key, value in nm_task.items() if not key.startswith('task_')}

    # print this
    # if nm_task['task_sync_status'] != 'ignored':
    # print('to be submitted:')
    # print(tm_task)
    # print()

    return tm_task
