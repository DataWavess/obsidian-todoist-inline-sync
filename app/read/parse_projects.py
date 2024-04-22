from variables import app_projects_location, nm_to_tm_folders_mapping, vault_location, nm_exclusion_folder_paths
from initialize.create_app_folders import store_tm_projects
from contact.tm_api import unarchive_project, create_project
import os
import json
import re



def get_tm_project(nm_task: dict, is_syncing_to_tm = True) -> str:
    """
    Iterates over a path of projects (i.e projects/create_app) that a task is supposed to be located in, in the todo manger
    When syncying to todo manager will then create or unarchive the projects that are in the path one by one.
    If not syncying will jut return the project.

    Returns:
        - A note manager project_id
    """
    
    # get project ids from local
    tm_projects = {}
    with open(app_projects_location, 'r') as f:
        tm_projects = json.load(f)
        
    
    # apply project from task
    tag_project_name = nm_task['task_tm_tag_project_path']
    # apply project from frontmatter

    # apply get project if in frontmatter
    frontmatter_project_name = nm_task.get('task_tm_frontmatter_project_path')
        
    # logic for folders
    folder_project_name = nm_task.get('task_tm_folder_project_path')

    # determine project namea
    tm_project_path = tag_project_name or frontmatter_project_name or folder_project_name or "Inbox" # default to inbox 

    # iterate over project path and handle tm project's existense
    tm_project_paths = tm_project_path.split('/')
    last_project_id = None
    for tm_path in tm_project_paths:
        current_path = tm_path
        # access project from projects list
        existing_project = tm_projects.get('name_based').get(current_path)
        if existing_project and current_path == existing_project.get('name'):
            if existing_project['is_archived']:
                unarchive_project(existing_project['id'])
                store_tm_projects() # update the project information after unarchiving
            last_project_id = existing_project.get('id')
        else:
            created_project = create_project(current_path, last_project_id)
            last_project_id = created_project.get('id')    
            #update the projects file for the newly created project
            store_tm_projects()

    # get ending project path name to get 
    project_to_use = tm_project_paths[-1]
    return str(last_project_id)


def get_tm_project_path(nm_task: dict):
    """
    Extracts a tasks mapped note manager project path based on regex in user configurations.
    For instance, a task located under "1 Projects/create_app" with corresponding capture regex of
    '(?i)1 Projects/([^/]*)' would return "1 Projects/create_app".

    Returns:
    - A string representation of the note_managers project.
    """
    tm_project_path = None

    # get task file path (and make it a standard unix path)
    task_file_location = nm_task['task_file_location']
    task_file_location = task_file_location.split(vault_location)[1]
    task_directory, task_file_location = os.path.split(task_file_location)
    task_file_location_parts = task_directory.split(os.path.sep) + [task_file_location]
    # remove part of the path if split has just the file seperator in it.
    task_file_location_parts = [part for part in task_file_location_parts if part]
    task_file_location = '/'.join(task_file_location_parts)

    # find nm folder path for task, if matches note manager folder capture paths
    for folder_mapping in nm_to_tm_folders_mapping.values():
        if re.match(folder_mapping['nm_capture_pattern'], task_file_location):
            # if in capture path, try to extract the dynamic nm_folder_path
            try:
                nm_folder_path = re.findall(folder_mapping.get('nm_folder_path'), task_file_location)[0]
            except:
                nm_folder_path = None
            
            # return none if there is still a {nm_folder_path} variable in tm_folder_path and no way to fill it
            current_tm_folder_path = folder_mapping.get('tm_folder_path')
            if (nm_folder_path is None and r'{nm_folder_path}' in current_tm_folder_path) or current_tm_folder_path is None:
                raise Exception('Tm_folder_path is Empty, or there is no variable provided for "nm_folder_path" variable defined in tm_folder_path.', ' task:', nm_task.get('task_name'), ' file: ', nm_task.get('task_file_location'))
            
            tm_project_path = current_tm_folder_path.replace(r'{nm_folder_path}', (nm_folder_path or ''))

            return tm_project_path # return early to apply the rule that first fits correctly

    return tm_project_path



def _get_tm_project_path(nm_task: dict):
    """
    Extracts a tasks mapped note manager project path based on regex in user configurations.
    For instance, a task located under "1 Projects/create_app" with corresponding capture regex of
    '(?i)1 Projects/([^/]*)' would return "1 Projects/create_app".

    Returns:
    - Records the capture patterns for where a task is found and where it is to go.
    """
    tm_project_path = None

    # get task file path (and make it a standard unix path)
    task_file_location = nm_task['task_file_location']
    task_file_location = task_file_location.split(vault_location)[1]
    task_directory, task_file_location = os.path.split(task_file_location)
    task_file_location_parts = task_directory.split(os.path.sep) + [task_file_location]
    # remove part of the path if split has just the file seperator in it.
    task_file_location_parts = [part for part in task_file_location_parts if part]
    task_file_location = '/'.join(task_file_location_parts)

    # find nm folder path for task, if matches note manager folder capture paths
    for folder_key, folder_mapping in nm_to_tm_folders_mapping.items():
        if re.match(folder_mapping['nm_capture_pattern'], task_file_location):
            # if in capture path, try to extract the dynamic nm_folder_path
            try:
                nm_folder_path = re.findall(folder_mapping.get('nm_folder_path'), task_file_location)[0]
            except:
                nm_folder_path = None
            
            # return none if there is still a {nm_folder_path} variable in tm_folder_path and no way to fill it
            current_tm_folder_path = folder_mapping.get('tm_folder_path')
            if nm_folder_path is None and r'{nm_folder_path}' in current_tm_folder_path:
                raise Exception('There is no variable provided for "nm_folder_path" variable defined in tm_project_path.', ' task:', nm_task.get('task_name'))
            tm_project_path = current_tm_folder_path.replace(r'{nm_folder_path}', (nm_folder_path or ''))
            
            # update task with values
            nm_task['task_nm_folder_capture_name'] = folder_key
            nm_task['task_nm_folder_capture_pattern'] = folder_mapping.get('nm_capture_pattern')
            nm_task['task_tm_folder_project_path'] = tm_project_path
            return None # return early to apply the rule that first fits correctly
    
    # if no captures apply None as the values
    nm_task['task_nm_folder_capture_name'] = None
    nm_task['task_nm_folder_capture_pattern'] = None
    nm_task['task_tm_folder_project_path'] = None

    return tm_project_path


def _get_nm_exclusion_path(nm_task: dict):
    """
    Extracts a tasks mapped note manager project path based on regex in user configurations.
    For instance, a task located under "1 Projects/create_app" with corresponding capture regex of
    '(?i)1 Projects/([^/]*)' would return "1 Projects/create_app".

    Returns:
    - Records the capture patterns for where a task is found and where it is to go.
    """
    tm_project_path = None

    # get task file path (and make it a standard unix path)
    task_file_location = nm_task['task_file_location']
    fslash_task_file_location = task_file_location.replace('\\', r'/')

    # find nm folder path for task, if matches note manager folder capture paths
    for exclusion_key, folder_mapping in nm_exclusion_folder_paths.items():
        if re.match(folder_mapping['nm_capture_pattern'], fslash_task_file_location):
            nm_task['task_nm_folder_exclusion_name'] = exclusion_key
            break

    if not nm_task.get('task_nm_folder_exclusion_name'):
        # if no exclusions apply None as values
        nm_task['task_nm_folder_exclusion_name'] = None

    return None
