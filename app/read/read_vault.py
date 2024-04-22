from variables import task_identifier_pattern, general_header_pattern, header_pattern, header_pattern_name, frontmatter_modified_date_field, nm_exclusion_folder_paths, app_location
from read.parse_tasks import parse_task_line
from read.parse_projects import _get_tm_project_path, _get_nm_exclusion_path
import os
import re
import json
from datetime import datetime

try: 
    with open(os.path.join(app_location, 'tm_tasks.json')) as f:
        tm_tasks = json.load(f)
except:
    tm_tasks = {}

try: 
    with open(os.path.join(app_location, 'projects.json')) as f:
        tm_projects = json.load(f)
except:
    pass

potential_task = []
task_group = {}

def read_note_metadata(vault_location:str) -> dict:
    """
    Reads medata from notes in vault
    
    """
    vault_notes = {}
    for folder, _, files in os.walk(vault_location):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(folder, file)
                # frontmatter settings
                is_in_frontmatter = False
                note_metadata = {}
                frontmatter_properties = {}
                with open(file_path, encoding='utf-8') as md:
                    i=0
                    for line in md:
                        i+=1
                        # check if line is in frontmatter
                        if i == 1 and line.startswith('---'):
                            is_in_frontmatter = True
                        elif is_in_frontmatter and line.startswith('---'):
                            is_in_frontmatter = False
                        # parse frontmatter
                        if is_in_frontmatter:
                            parse_frontmatter(line, frontmatter_properties)

                        # DEPRECATED - not necessary. Will read this on writeback
                        # # get header for drop off location
                        # current_header = re.compile(header_pattern).match(line)
                        # current_header = current_header.group(1) if current_header else None
                        # if current_header and current_header ==  header_pattern_name:
                        #     note_metadata['note_beacon_drop_off_md_line'] = i
                        #     break

                        # break if out of frontmatter
                        if not is_in_frontmatter:
                            break

                    # at end of reading, update note metadata
                    note_metadata['note_file_name'] = os.path.splitext(os.path.basename(file_path))[0]
                    note_metadata['note_file_location'] = file_path
                    note_metadata['note_file_modified_date'] = os.path.getmtime(file_path)
                    note_metadata['note_frontmatter_properties'] = frontmatter_properties
                    frontmatter_modified_date = None
                    for property, value in frontmatter_properties.items():
                        if property == frontmatter_modified_date_field:
                            frontmatter_modified_date = value
                            break
                    note_metadata['task_frontmatter_modified_date'] = frontmatter_modified_date
                    if frontmatter_modified_date:
                        datetime_pattern = r'\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?'
                        match = re.search(datetime_pattern, frontmatter_modified_date)
                        if match:
                            extracted_date = match.group(0)
                            try:
                                formatted_date = datetime.strptime(extracted_date, "%Y-%m-%d %H:%M:%S")
                            except:
                                formatted_date = datetime.strptime(extracted_date, "%Y-%m-%d")
                            note_metadata['task_frontmatter_modified_date'] =  str(formatted_date)
                    # apply beacon
                    note_metadata['note_tm_beacon'] = note_metadata['note_frontmatter_properties'].get('tm_beacon')
                    # apply if note is an archive note
                    for exclusion, exclusion_rule in nm_exclusion_folder_paths.items():
                        if exclusion_rule.get('nm_is_archive_folder'):
                            if re.match(exclusion_rule['nm_capture_pattern'], file_path.replace('\\', r'/')):
                                note_metadata['note_is_in_archive'] = True
                                break
                    vault_notes[note_metadata['note_file_location']] = note_metadata
    return vault_notes


def read_notes(vault_location:str, return_task_type='task') -> dict:
    """
    Iterates over a given folder or file and reads all makrdown files
    for any lines that match a task regex.

    Parameters:
    - vault_location: A folder that represent a obsidian vault
    - return_task_type = ('task', 'potential_task')

    Returns:
    - A dict of markdown files containing a list of dictionaries. 
    Each dictionary corresponds to a task found in each line of the note.
    """
    if os.path.isfile(vault_location):
        is_file = True
    else:
        is_file = False

    vault_notes = {}
    vault_tasks = {}
    def read_file(filename):
        if filename.endswith('.md'):
            if is_file:
                file_path = filename
            else:
                file_path = os.path.join(folder, filename)
            
            # Exclude file from parsing if its part of the exclusion path
            is_excluded_path = False
            fslash_file_path = file_path.replace('\\', r'/')
            for exclusion, exclusion_rule in nm_exclusion_folder_paths.items():
                if exclusion_rule.get('nm_ignore_path_from_task_parsing'):
                    if re.match(exclusion_rule['nm_capture_pattern'], fslash_file_path):
                        is_excluded_path = True
                        break
            # if is excluded path then return empty list for file
            if is_excluded_path:
                vault_notes[file_path] = []
            else:
                note_task, note_task_task = read_note_task(file_path)
                vault_notes[file_path] = note_task
                vault_tasks.update(note_task_task)
        
    if is_file:
        read_file(vault_location)
    else:    
        for folder, sub_folders, files in os.walk(vault_location):
            for file in files:
                read_file(file)
                
    # store the note tasks
    with open(os.path.join(app_location, 'nm_potential_tasks.json'), 'w') as f:
        json.dump(potential_task, f)
        
    return vault_notes, vault_tasks
     

def read_note_task(note: str) -> list:
    """
    Iterates over a markdown file and parses out task contained within.
    If no task are found returns empty list

    Parameters:
    - note(str): A path on the file system 

    Returns: 
    - a list of dicts, each representing a task found on a line.
    """
    with open(os.path.join(app_location, 'projects.json')) as f:
        tm_projects = json.load(f)

    note_tasks = []
    note_task_tasks = {}
    current_header = None
    is_in_frontmatter = False
    with open(note, encoding='utf-8') as md:
        i=0
        frontmatter_properties = {}
        for line in md:
            i+=1
            # check if line is in frontmatter
            if i == 1 and line.startswith('---'):
                is_in_frontmatter = True
            elif is_in_frontmatter and line.strip() == '---':
                is_in_frontmatter = False
            # parse frontmatter
            if is_in_frontmatter:
                parse_frontmatter(line, frontmatter_properties)
            # get markdown heading text
            current_header_match = re.compile(general_header_pattern).match(line)
            current_header = current_header_match.group(0) if current_header_match else current_header
            # parse task
            task = parse_task(line, i, is_in_frontmatter)
            if task:
                # store additional metadata about the task
                task['task_md_line'] = i
                task['task_file_name'] = os.path.splitext(os.path.basename(note))[0]
                task['task_file_location'] = note
                task['task_file_mtime'] = os.path.getmtime(note)
                task['task_header'] = current_header
                task['task_frontmatter_properties'] = frontmatter_properties
                task['task_key'] = 'file:' + task['task_file_location'].replace('\\', '/') + '|line:' + str(task['task_md_line'])
                # apply task associated information
                task['task_tm_associated_parent_id'] = tm_tasks.get(str(task['task_tm_link_id']), {}).get('parent_id')
                task_associated_project_id = tm_tasks.get(str(task['task_tm_link_id']), {}).get('project_id')
                task['task_tm_associated_project_name'] = tm_projects['id_based'].get(task_associated_project_id, {}).get('name')
                # store frontmatter properties
                frontmatter_modified_date = None
                for property, value in frontmatter_properties.items():
                    if property == frontmatter_modified_date_field:
                        frontmatter_modified_date = value
                        break
                # store frontmater dates
                task['task_frontmatter_modified_date'] = frontmatter_modified_date
                if frontmatter_modified_date:
                    datetime_pattern = r'\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?'
                    match = re.search(datetime_pattern, frontmatter_modified_date)
                    if match:
                        extracted_date = match.group(0)
                        try:
                            formatted_date = datetime.strptime(extracted_date, "%Y-%m-%d %H:%M:%S")
                        except:
                            formatted_date = datetime.strptime(extracted_date, "%Y-%m-%d")
                        task['task_frontmatter_modified_date'] =  str(formatted_date)
                # store capture and exclusion data in task
                store_capture_rules(task)
                # store task group
                store_task_group(task)
                # append the task to the notes list
                note_tasks.append(task)
                # append the task to the dict holding all tasks
                note_task_tasks[task['task_key']] = task
                
            else:
                task_group = {} # reset task group if task group was broken

    return note_tasks, note_task_tasks


def parse_task(line: str, line_number: int, is_in_frontmatter: bool) -> dict:
    """
    Parses a line/string looking for task identifier `- [.]`. If found will parse
    out the details of the task according the libraries task definitions

    Parameters: 
    - line(str): a string representation of a line.

    Returns:
    - A dict of task information
    """
    try:
        # Find the task identifier
        task_identifier = re.match(task_identifier_pattern, line).group(0)
    except:
        return None # no task string (ex: "- [.]" ) found
    if task_identifier:
        try:
            # Use re.search to find the task
            task = parse_task_line(line, line_number)
        except Exception as e:
            potential_task.append(line) # store potential task
            return None
        
    return task
 

def parse_frontmatter(line, frontmatter_properties):
    property_match = re.search(r'.*:', line)
    value_match = re.search(r'(?<=: ).*', line)
    if property_match:
        property_name = property_match.group(0).split(':')[0]
        try:
            property_value = value_match.group(0)
        except:
            property_value = None ## this is to avoid issues when parsing mutli line properties
        frontmatter_properties[property_name] = property_value
    return None


def store_capture_rules(task: dict) -> None:
    """ Checks if task falls within any of the capture rules 
    for storing the task in a specific todo manager path
    and;
    for ignoring a task from being pushed to the todo manager

    Returns:
        None, data is stored in the task.
    """ 
    # store project path based on file location and user capture rules
    _get_tm_project_path(task)
    _get_nm_exclusion_path(task)
    # store project path based on frontmatter
    task['task_tm_frontmatter_project_path'] = task.get('task_frontmatter_properties').get('tm_project')
    task['task_tm_project_path'] = task['task_tm_tag_project_path'] or task['task_tm_frontmatter_project_path'] or task['task_tm_folder_project_path']  or "Inbox" # default to inbox
    task['task_tm_project_path_name'] = task['task_tm_project_path'].split('/')[-1]
    
    return None


def test_read_folder_locations(folder:str):
    """
    testing code
    """
    for folder, _, files, in os.walk(folder):   
        for file in files:
            path = os.path.join(folder,file)
            if file.endswith('.md'):
                print(path)
    return None


def store_task_group(task):
    current_task_info = {}
    current_task_info = {
        'task_level': task['task_level'],
        'task_tm_project_path': task['task_tm_project_path'],
        'task_key': task['task_key'],
    }
    
    if task['task_level'] == 0:
        current_task_info['task_group_key'] = task['task_key']
        task_group[task['task_level']] = current_task_info
        task['task_group_parent_key'] = None
    elif task['task_level'] <= 10:
        if task['task_tm_project_path'] == task_group[task['task_level']-1]['task_tm_project_path'] \
            and task['task_tm_project_path'] == task_group[0]['task_tm_project_path']:
            current_task_info['task_group_key'] = task_group.get(0)['task_group_key']
            task_group[task['task_level']] = current_task_info
            task['task_group_parent_key'] = task_group[task['task_level']-1]['task_key']
    

    task['task_group_parent_key'] = task.get('task_group_parent_key') # apply None if there is none
    task['task_group_parent_main_key'] = task_group[0]['task_group_key']

    return task