from datetime import datetime, timedelta, timezone
import re
from variables import frontmatter_modified_date_field, frontmatter_modified_date_format


def determine_task_change_status(nm_task:dict, current_run_time: object, tm_tasks:dict, sync_logic: object) -> str:
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
    # 1st main reasons - closed already, ignoreable, cancelled or deleted from being worked on
    # 2nd main reason - the task is a completed recurrence task
    if (task_checkbox_status in ('close', 'ignore', 'cancel', 'delete') and not task_id):
        nm_task['task_tm_status'] = 'ignore:by_checkbox_status_and_no_tm_id'
        return 'ignore:by_checkbox_status/no_tm_id'
    
    if task_recurrence and task_checkbox_status == 'close':
        nm_task['task_tm_status'] = 'ignore:recurrence'
        return 'ignore:recurrence'
    
    if (task_checkbox_status in ('close', 'ignore', 'cancel', 'delete') and not tm_tasks.get(task_id)):
        nm_task['task_tm_status'] = 'ignore:deleted/cancelled'
        return 'ignore:by_checkbox_status/tm_id is no longer active already'
    
    # determine the date of the file and ignore based on recentness of file
    if sync_logic:
        sync_types = sync_logic.get('sync_types')
    else:
        sync_types = None
    
    if sync_types:
        file_date = datetime.utcfromtimestamp(nm_task.get('task_file_mtime')).replace(tzinfo=timezone.utc)
        try:
            frontmatter_date = nm_task.get('task_frontmatter_properties').get(frontmatter_modified_date_field)
            frontmatter_date = datetime.strptime(frontmatter_date, frontmatter_modified_date_format)
        except:
            frontmatter_date = None
            
        sync_period = sync_logic.get('sync_period')
        comparison_date = None
        sync_type_choices = []
        for sync_type in sync_types:
            if sync_type == 'file':
                sync_type_choices.append(file_date)
            if frontmatter_date and sync_type == 'frontmatter':
                sync_type_choices.append(frontmatter_date)
        comparison_date = sync_type_choices[0]

        # if there is a sync_app setting use that is the start time to pull hte data
        if sync_logic.get('sync_app_timestamp'):
            lookback_period = sync_logic.get('sync_app_timestamp')
        else:
            lookback_period = current_run_time - timedelta(minutes = sync_period)
            
        # compare the comparisson date if there is one to apply selective file date sync
        if comparison_date and comparison_date < lookback_period:
            nm_task['task_tm_status'] = 'ignore:by_modified_time'
            return 'ignore:by_modified_time'

    # Determine task_tm_sync_status for task that have a todo manager id already
    try:
        api_task = tm_tasks[task_id]
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