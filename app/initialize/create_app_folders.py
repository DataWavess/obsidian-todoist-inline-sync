from variables import app_location, header_pattern_name
from contact.tm_api import get_projects_async, get_projects, get_tasks_async, get_archived_projects, get_reminders, get_completed_resources
import asyncio
import os
import json

# functions

def create_folders(func):
    """ 
    Creates path if does not exist.
    
    """
    def inner_func(path):
        path_location = os.path.join(app_location, path)
        if not os.path.exists(os.path.dirname(path_location)):
            os.makedirs(os.path.dirname(path_location))
        return func(path)
    return inner_func

@create_folders
def store_reminders(file_name):
    reminders = get_reminders()
    reminders_location = os.path.join(app_location, file_name)
    with open(reminders_location, 'w') as f:
        json.dump(reminders_location, f)
    return reminders

@create_folders
def store_active_tasks(file_name):
    active_tasks = asyncio.run(get_tasks_async())
    active_tasks_location = os.path.join(app_location, file_name)
    with open(active_tasks_location, 'w') as f:
        json.dump(active_tasks, f)
    return active_tasks

@create_folders
def store_closed_tasks(file_name:str):
    """
    Stores closed task:
        - closed task instances by instance id
        - closed task that have ever been closed. Only the latest completion is stored.
    Return:
        - closed task instances by instance id
    """
    closed_tasks = get_completed_resources('items')
    closed_tasks_location = os.path.join(app_location, file_name)

    # format closed task instances
    formatted_closed_tasks_instances = {}
    for task in closed_tasks:
        formatted_closed_tasks_instances[str(task.get('id'))] = task

    with open(closed_tasks_location, 'w') as f:
        json.dump(formatted_closed_tasks_instances, f)

    # format closed task as a list - ignoring the many instances of a closed task for recurrence
    formatted_closed_tasks = {}
    for task in reversed(closed_tasks):
        formatted_closed_tasks[str(task.get('task_id'))] = task

    # pull all the historically closed tasks
    closed_tasks_historical_location = os.path.join(app_location, 'tm_tasks_closed_historically.json')
    if not os.path.exists(os.path.dirname(closed_tasks_historical_location)):
        os.makedirs(closed_tasks_historical_location)
    with open(closed_tasks_historical_location, 'a+') as f:
        try:
            closed_tasks_historical = json.load(f)
        except:
            closed_tasks_historical = {}
        all_closed_tasks_historical = {**closed_tasks_historical, **formatted_closed_tasks}
        f.truncate(0)
        # put all new closed task and add them to the closed task historical file.
        json.dump(all_closed_tasks_historical, f)

    return formatted_closed_tasks_instances

@create_folders
def store_tasks(file_name):
    active_tasks = store_active_tasks('tm_tasks.json')
    closed_tasks = store_closed_tasks('tm_tasks_closed_instances.json')
    active_tasks.update(closed_tasks)
    all_tasks = active_tasks
    file_location = os.path.join(app_location, file_name)
    # Deprecated - storing task in more files
    # with open(file_location, 'w') as f:
    #     json.dump(all_tasks, f)
    return all_tasks

@create_folders
def replace_inbox_file(file_name):
    with open(file_name, 'w') as f:
        f.write(f'\n## {header_pattern_name}\n')
    return None

# store task into the markdown files
def store_tm_projects(pull_archived_projects:bool=False):
    """
    Writes projects that exists in todo manager into a file in app folder.

    Returns:
    - Returns a dict that has the projects. The dicts are duplicated by using the project name as a key 
    and the project id as another key

    """
    projects = get_projects()
    project_ids = {} 
    project_names = {}
    for project in projects:
        project = project.__dict__
        project_ids[project['id']] = project

    for project in project_ids.values():
        project['is_archived'] = False

    # get archived projects
    if pull_archived_projects:
        archived_projects = get_archived_projects()
        project_ids = {**project_ids, **archived_projects}

    # apply full path 
    for project in project_ids:
        lineage_ids = get_parent_projects(project_ids, str(project))
        project_ids.get(project)['project_path'] = get_lineage_path(project_ids, lineage_ids)

    # create a named based dict
    for project in project_ids:
        project_names[project_ids[project]['name']] = project_ids[project]

    projects = {
            'id_based': project_ids, 
            'name_based': project_names,
    }
    
    # Check if the directory already exists for projects
    if not os.path.exists(app_location):
        os.makedirs(app_location)

    # store projects
    with open(os.path.join(app_location, 'projects.json'), 'w', encoding='utf-8') as file:
        json.dump(projects, file)

    return projects

def get_parent_projects(data:dict, child_id:str):
    """
    Returns a list of parents. Starting with the progenitor.

    Parameters:
    - Data: Dict of projects with dict key being the project_key.

    Returns:
    - A list of parents, starting with the progenitor, ending with provided child.

    """
    lineage = [child_id]

    while child_id in data:
        parent_id = data[child_id].get('parent_id')
        if parent_id is not None:
            lineage.append(parent_id)
            child_id = parent_id
        else:
            break
    lineage.reverse()
    return lineage


def get_lineage_path(data:dict, lineage: list) -> list:
    """
    Creates a directory path of from a list of parents and children paths.

    Returns:
    - A full path string
    """
    named_lineage = []
    for project in lineage:
        named_lineage.append(data.get(project).get('name'))

    full_project_path = os.path.join(*named_lineage)
    return full_project_path



def create_md_lines(todoist_object: object, selected_fields: dict, linkable_field=[]) -> list:
    """
    This function will format the todoist data in the object as a concatenated string and
    return these strings in a list. Will also 

    Parameters: 
    - todoist_object(object): The named tuple that todoist returns for its objects
    - selected_fields(dict): a dict of items to include in the formatted line. 
        - Key is the id used by todoist in its fields
        - Value is the name to be used to store the value.

    Returns:
    - Will return a list of these formatted lines.
    """
    # Iterate through the selected fields and format them into Markdownk
    md_lines = []
    for object in todoist_object:
        markdown_fields = []
        markdown_line = []
        for field, label in selected_fields.items():
            if field in linkable_field:
                label_value = '[[' + getattr(object, field) + ']]'
            else:
                label_value = getattr(object, field)
            markdown_fields.append(f"{label}: {label_value}")
            # Combine the Markdown field-value pairs into a single Markdown line
            markdown_line = " | ".join(markdown_fields)
        md_lines.append(markdown_line)
    return md_lines

        
def store_todo_tasks():
    tasks = asyncio.run(get_tasks_async())
    
    # Create a dictionary to map field names to their labels
    field_labels = {
        'id': 'id',
        'project_id': 'project_id',
        'section_id': 'section_id', 
        'content': 'name',
        'priority': 'priority',
        'created_at': 'created_at',
        'due': 'due',
        'labels': 'labels',
    }
    linkable_fields = [
     'name',
    ]

    # Initialize an empty list to store the Markdown field-value pairs
    md_lines = create_md_lines(tasks, field_labels, linkable_fields)
    
    # Write the Markdown line to the MD file
    with open(app_location + '/tasks.md', 'w', encoding='utf-8') as md_file:
        for line in md_lines:
            md_file.write(line + '\n')

