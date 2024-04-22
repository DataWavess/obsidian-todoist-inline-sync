import re
from variables import task_starter_chars
from variables import tm_task_date_signals, tm_task_recurrence_signals, tm_task_recurrence_signals, tm_priority_names \
    , tm_priority_to_nm_priority_mapping, task_checkbox_statuses, task_status_types, user_task_extraction_regexes


def parse_task_line(input:str, line_number:int) -> list: 
    """
    Parses out the parameters representing a task.
    Anything not found will not be included in the return value.

    Returns:
    A dictionary with parameters for the task.
    """
    task = {}

    # task level
    task['task_level'] = len(input) - len(input.lstrip())

    # apply parent heading id if there is one
    if task['task_level'] > 0:
        task['task_parent_md_line'] = line_number - 1
        
    # Regular expression for matching dates and icons
    date_icon_pattern = f"([{tm_task_date_signals}]) (\d{{4}}-\d{{2}}-\d{{2}}(?: (?:[0-2]?[0-9]:[0-5]?[0-9]))?)"
    date_pairs = re.findall(date_icon_pattern, input)

    # Seperate date pairs
    task_dates = {}
    for icon, date in date_pairs:
        # Iterate through the task details and match them with task starter characters
        for starter_char, key in task_starter_chars.items():
            if icon.startswith(starter_char):
                task_dates[key] = date.strip()
                break
    
    task['task_dates'] = task_dates

    # check if a reminder has been submitted to todo manager
    if  task_dates.get('reminder_date') and '🔔' in input:
        task['task_reminder_notification_exists'] = True
    else:
        task['task_reminder_notification_exists'] = False

    # Extraction of recurrence rule
    recurrence_pattern = fr"{tm_task_recurrence_signals}(.*?)(?=(" + "|".join(map(re.escape, (tm_task_date_signals + '#'))) + r")|$)"
    match = re.search(recurrence_pattern, input)
    task['task_recurrence'] = match.group(1) if match else None

    # Extraction of priority
    for key in tm_priority_to_nm_priority_mapping.keys():
        # Check if the key is in the input string
        if key in input:
            # Extract the corresponding value from the dictionary
            task['task_priority'] = tm_priority_to_nm_priority_mapping[key]
            task['task_priority_name'] = tm_priority_names[key]
            break
    

    # Extracting task_labels (tags in obsidian)
    label_pattern = r'(#\S+)'  # Matches hashtags followed by non-space characters
    task['task_labels'] = re.findall(label_pattern, input)

    # Extracting todoist id
    tm_link_pattern = r'\[Todoist\]\(https://todoist\.com/showTask\?id=([0-9]*)\)'  # Matches text within square brackets and parentheses
    tm_link_match = re.search(tm_link_pattern, input)
    task['task_tm_link'] = tm_link_match.group(0) if tm_link_match else None
    task['task_tm_link_id'] = tm_link_match.group(1) if tm_link_match else None

    # Create a regex pattern to match any of the task icon starters
    task_starter_pattern = '|'.join(re.escape(starter) for starter in task_starter_chars.keys())

    # split task to its own name. task_name_full, includes checkbox 
    task_name_full = re.split(fr'({task_starter_pattern})', input)[0]
    task['task_checkbox_prefix'] = re.search('((?:\d+\.|[+*-])) \[.?].*', task_name_full).group(1)
    task['task_checkbox'] = re.search(fr'.*(\[.?]) (.*)', task_name_full).group(1)
    task['task_checkbox_symbol'] = re.search(fr'.*\[(.?)] (.*)', task_name_full).group(1)
    task['task_checkbox_next_symbol'] = task_checkbox_statuses.get(task['task_checkbox_symbol']).get('task_next_status_symbol')
    task['task_checkbox_status_name'] = task_checkbox_statuses.get(task['task_checkbox_symbol']).get('task_status_name')
    task['task_checkbox_status_type'] = task_checkbox_statuses.get(task['task_checkbox_symbol']).get('task_status_type')
    task['task_checkbox_status'] = task_status_types.get(task['task_checkbox_status_type'])
    task['task_name'] = re.search(fr'.*(\[.?]) (.*)', task_name_full).group(2).strip()

    # parse user task for their defined patters
    task['task_user_patterns']=[]
    for user_pattern_key, user_pattern in user_task_extraction_regexes.items():
        user_regex = user_pattern.get('regex')
        user_match = re.match(user_regex, input)
        if user_match:
            user_matched_value = user_match.group(1)
            user_data_type = user_pattern.get('data_type', 'str')
            try:
                if user_data_type == 'int':
                    user_matched_value = int(user_matched_value)
                elif user_data_type == 'float':
                    user_matched_value = float(user_matched_value)
                elif user_data_type == 'date':
                    user_matched_value = str(date(user_matched_value)) # cant store date in json for excel
            except Exception as e:
                user_matched_value = user_matched_value
            pattern_dict = {
                'pattern_name': user_pattern.get('regex_name'),
                'pattern_value': user_matched_value,
            }
            task['task_user_patterns'].append(pattern_dict)
            
    # with parsed user task, create a 
    for found_pattern in task['task_user_patterns']:
        name = found_pattern.get('pattern_name')
        task[f'task_user_{name}'] = found_pattern.get('pattern_value')

    # parse out tm project path based on tag 
    parse_project_from_tag(task)
    
    return task


def parse_project_from_tag(nm_task: object) -> str:
    
    
    # apply logic for getting the project name from the label
    pattern = r'(?:#projects)/(\w|/|-)+'
    project_match = re.search(pattern, str(nm_task['task_labels']))
    
    if project_match:
        tag_project_name =  project_match.group(0).replace('#projects/', '')
    else:
        tag_project_name = None
    nm_task['task_tm_tag_project_path'] = tag_project_name

    return tag_project_name


