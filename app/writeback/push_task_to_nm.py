from variables import task_starter_chars_swapped, tm_priority_to_nm_priority_mapping_swapped, tm_task_recurrence_signals, header_pattern
import re
from datetime import datetime
import copy


def push_task_to_nm(td_nm_tasks, note):
    # read the file first
    with open(note, 'r+', encoding='utf-8') as file:
        lines = file.readlines()

    # read the task and overwrite the lines
    for td_nm_task in td_nm_tasks:
        task_line = td_nm_task['task_md_line']

        new_task_line_content = create_md_line_from_task(td_nm_task)

        if len(lines) > (task_line - 1):
            lines[task_line-1] = new_task_line_content

    # overwrite the file
    with open(note, 'w', encoding='utf-8') as file:
        file.writelines(lines)

    return None

def push_new_recurring_completion_task_to_nm(td_nm_tasks, note):
    # Sort the list of task based on 'task_recurrence_parent_md_line'
    # in order to avoid losing the line number of the parent recurring task
    td_nm_tasks = sorted(td_nm_tasks, key=lambda x: (-x.get('task_recurrence_parent_md_line', 0), x.get('task_recurrence_completed_date', '')))
    # read the file first
    with open(note, 'r+', encoding='utf-8') as file:
        lines = file.readlines()

    # read the task and overwrite the lines
    i = 1
    for td_nm_task in td_nm_tasks:
        parent_id = td_nm_task['task_tm_link_id']
        parent_task_line = td_nm_task['task_recurrence_parent_md_line']
        if i == 1:
            main_parent_id = parent_id
            # update the parent recurrence task due dates before inserting the new missing completions
            # only update if the due date is before the current due date from the todo manger
            if td_nm_task['task_recurrence_parent_due_date'] < td_nm_task['task_recurrence_tm_active_due_date']:
                artificial_parent_td_nm_task = copy.deepcopy(td_nm_task)
                artificial_parent_td_nm_task['task_checkbox'] = '[ ]'
                artificial_parent_td_nm_task['task_checkbox_next_symbol'] = ' '
                artificial_parent_td_nm_task['task_checkbox_status'] = 'open'
                artificial_parent_td_nm_task['task_dates']['due_date'] = td_nm_task['task_recurrence_tm_active_due_date']
                artificial_parent_td_nm_task['task_dates']['completed_date'] = None
                new_task_line_content = create_md_line_from_task(artificial_parent_td_nm_task)
                lines[parent_task_line - 1] = new_task_line_content

        if i > 1 and parent_id != main_parent_id:
            main_parent_id = parent_id
            i = i


        task_line = parent_task_line + 1
        new_task_line_content = create_md_line_from_task(td_nm_task)
        lines.insert(task_line-1, new_task_line_content)
        # update the parent recurrence task due dates before moving to another one
        i+=1

    # overwrite the file
    with open(note, 'w', encoding='utf-8') as file:
        file.writelines(lines)

    return None

def push_new_task_to_nm(td_nm_tasks, note):
    # read the file first
    md_note_start_line = None
    md_new_task_header_line = None
    found_frontmatter = False
    with open(note, 'r+', encoding='utf-8') as file:
        lines = file.readlines()
        i = 0
        for line in lines:
            i+= 1
            if re.match(header_pattern, line):
                md_new_task_header_line = i
            if re.match('---', line):
                if found_frontmatter:
                    md_note_start_line = i
                found_frontmatter = True

    # determine task line to start writing to
    md_new_task_line = None
    if md_new_task_header_line:
        md_new_task_line = md_new_task_header_line + 1
    elif md_note_start_line:
        md_new_task_line = md_note_start_line + 1
    else:
        md_new_task_line = 1

    # read the task and overwrite the lines
    written_lines = md_new_task_line - 1
    for td_nm_task in td_nm_tasks:
        task_line = md_new_task_line
        new_task_line_content = create_md_line_from_new_tm_task(td_nm_task)
        lines.insert(written_lines, new_task_line_content)
        written_lines+=1

    # overwrite the file
    with open(note, 'w', encoding='utf-8') as file:
        file.writelines(lines)

    return None


def create_md_line_from_task(nm_task: dict) ->str:
    """
    Takes a task and creates a string reprenting a task line in a note manager.

    Returns:
    - String representation of a task.
    """
    task = nm_task
    indent = '\t' * task['task_level']
    checkbox_prefix = task['task_checkbox_prefix']
    checkbox = task['task_checkbox']
    task_name = task['task_name']
    
    # get task dates
    task_completed_date = task['task_dates'].get('completed_date')
    task_created_date = task['task_dates'].get('created_date')
    task_meta_dates = None
    if task_created_date:
        task_meta_dates = f'{task_meta_dates or ""}{task_starter_chars_swapped.get("created_date")} {task_created_date} '
    if task_completed_date:
        task_meta_dates = f'{task_meta_dates or ""}{task_starter_chars_swapped.get("completed_date")} {task_completed_date} '
    
    # get recurrence
    if task['task_recurrence']:
        recurrence_rule = task['task_recurrence']
        recurrence = tm_task_recurrence_signals[0] + ' '+ recurrence_rule.strip() + ' '
    else:
        recurrence = None
    
    # create the task_date string
    task_meta_date_names = ['created_date', 'completed_date']
    task_additional_info_names = ['reminder_date']
    task_info_dates = None
    task_additional_info_dates = None
    for task_date_name, task_date in task['task_dates'].items():
        if task_date_name not in task_meta_date_names:
            if task_date_name in task_additional_info_names:
                task_additional_info_dates = f'{task_additional_info_dates or ""}{task_starter_chars_swapped.get(task_date_name)} {task_date} '
            else:
                task_info_dates = f'{task_info_dates or ""}{task_starter_chars_swapped.get(task_date_name)} {task_date} '
    
    if task_additional_info_dates and nm_task['task_reminder_notification_exists']:
        task_additional_info_dates = '🔔' + task_additional_info_dates

    # priority
    priority = tm_priority_to_nm_priority_mapping_swapped.get(task.get('task_priority'))
    if priority:
        priority = priority + ' '
    
    # tags
    tags = task.get('task_labels')
    if tags:
        tags = list(set(task.get('task_labels')))
    task_tags = None
    if tags:
        for tag in tags:
            task_tags = f'{task_tags or ""}{tag} '

    # links
    tm_link = task.get('task_tm_link')
    if tm_link:
        tm_link = tm_link + ' '


    task_representation = f'{indent}{checkbox_prefix} {checkbox} {task_name} {tm_link or ""}{priority or ""}{task_additional_info_dates or ""}{recurrence or ""}{task_info_dates or ""}{task_tags or ""}{task_meta_dates or ""}'.rstrip() + '\n'
    return task_representation


def create_md_line_from_new_tm_task(task: dict) ->str:
    """
    Takes a task and creates a string reprenting a task line in a note manager.

    Returns:
    - String representation of a task.
    """
    indent = '\t' * (1 if task['task_parent_id'] else 0) #if has parent_id at least indent it
    checkbox_prefix = '-'
    checkbox = '[ ]'
    task_name = task['task_name']
    
    # get task dates
    task_completed_date = task['task_dates'].get('completed_date')
    task_created_date = task['task_dates'].get('created_date')
    task_meta_dates = None
    if task_created_date:
        task_meta_dates = f'{task_meta_dates or ""}{task_starter_chars_swapped.get("created_date")} {task_created_date} '
    if task_completed_date:
        task_meta_dates = f'{task_meta_dates or ""}{task_starter_chars_swapped.get("completed_date")} {task_completed_date} '
    
    # get recurrence
    if task['task_recurrence']:
        recurrence_rule = task['task_recurrence']
        recurrence = tm_task_recurrence_signals[0] + recurrence_rule.rstrip() + ' '
    else:
        recurrence = None
    
    # create the task_date string
    task_meta_date_names = ['completed_date', 'created_date']
    task_info_dates = None
    for task_date_name, task_date  in task['task_dates'].items():
        if (task_date_name not in task_meta_date_names) and task_date:
            task_info_dates = f'{task_info_dates or ""}{task_starter_chars_swapped.get(task_date_name)} {task_date} '
        
    # priority
    priority = tm_priority_to_nm_priority_mapping_swapped.get(task.get('task_priority'))
    if priority:
        priority = priority + ' '
    
    # tags
    tags = task.get('task_labels')
    task_tags = None
    if tags:
        for tag in tags:
            task_tags = f'{task_tags or ""}{tag} '

    # links
    tm_link = task.get('task_tm_link')
    if tm_link:
        tm_link = tm_link + ' '

    # grouped sections
        # ({recurrence or ""}{task_info_dates or ""})
    task_representation = f'{indent}{checkbox_prefix} {checkbox} {task_name} {tm_link or ""}{priority or ""}{recurrence or ""}{task_info_dates or ""}{task_tags or ""}{task_meta_dates or ""}'.rstrip() + '\n'
    
    return task_representation
