from read.read_vault import read_note_metadata, read_notes
from variables import vault_location, app_location, inbox_location, dashboard_location, namespace_location, td_todo_tags, td_todo_prefix, sync_logic
from datetime import datetime, timezone, timedelta
import json
import os
import argparse


def read_vault_note_metadata(working_path=vault_location):
    """
    Reads vault notes, extracting metadata, and stores the data in app folder.
    """
    notes_metadata = read_note_metadata(working_path)
    with open(os.path.join(app_location, 'note_metadata.json'), 'w') as f:
        json.dump(notes_metadata, f)

    # write the projects and tags to a namespace to have them available
    tag_project_list = \
        ['#projects/' + note.get('note_frontmatter_properties', {}).get('tm_project') for key, note in notes_metadata.items() if note.get('note_frontmatter_properties', {}).get('tm_project')] + \
        ['#projects/' + note.get('note_frontmatter_properties', {}).get('tm_beacon') for key, note in notes_metadata.items() if note.get('note_frontmatter_properties', {}).get('tm_beacon')] 
    tag_project_list = set(tag_project_list)
    tag_tag_list = ['#' + td_todo_prefix + '/' + tag for tag in td_todo_tags]
    tag_tag_list = set(tag_tag_list)
    
    with open(namespace_location, 'w') as f:
        f.write('\n## projects\n')
        for item in tag_project_list:
            f.write(item + '\n')

        f.write('## tags\n')
        for item in tag_tag_list:
            f.write(item + '\n')
        
    return notes_metadata

def read_vault_notes(working_path=vault_location, open_excel=False):
    """
    Reads the notes in the vault and will write them to a task file.
    Opens dashboard excel file afterwards.
    """
    vault_read_start_time = datetime.now(timezone.utc)

    ## read nm task
    notes_nm_task, nm_tasks_keys = read_notes(working_path)
    with open(os.path.join(app_location, 'nm_tasks.json'), 'w') as f:
        json.dump(notes_nm_task, f)
    with open(os.path.join(app_location, 'nm_tasks_keys.json'), 'w') as f:
        json.dump(nm_tasks_keys, f)

    if open_excel:
        os.system(fr'start excel "{dashboard_location}"')
    
    # notify of vault read time
    vault_read_end_time = datetime.now(timezone.utc)
    read_time = round((vault_read_end_time - vault_read_start_time).total_seconds() / 60, 2)

    print(f'Finished: Reading Vault Notes In {read_time} minutes')
    return notes_nm_task, nm_tasks_keys


read_vault_notes(open_excel=True)
read_vault_note_metadata()