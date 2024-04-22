from read.read_vault import read_note_metadata, read_notes
from read.read_beacons import store_project_beacons
from contact.push_task_to_tm import sync_task_to_tm
from contact.batch_push_task_to_tm import batch_sync_task_to_tm
from contact.batch_push_project_to_tm import batch_archive_projects
from contact.tm_api import get_last_activity_since_timestamp
from initialize.create_app_folders import store_tm_projects, store_reminders, store_tasks, store_active_tasks, replace_inbox_file
from writeback.writeback_to_nm import writeback_td_task_to_nm, writeback_since_sync_to_nm, writeback_new_task_lines_to_nm
from convert.task_unpacker import unpack_nm_note_task, get_missing_recurring_completions
from variables import vault_location, app_location, inbox_location, dashboard_location, namespace_location, td_todo_tags, td_todo_prefix, sync_logic
from datetime import datetime, timezone, timedelta
import json
import os
import argparse
# func_run_time = datetime.now(timezone.utc)
# print('storing projects', (datetime.now(timezone.utc) - func_run_time).total_seconds())
# update todo data - before any operation  
func_run_time = datetime.now(timezone.utc)
stored_projects = store_tm_projects(pull_archived_projects=True)
# print('storing projects', (datetime.now(timezone.utc) - func_run_time).total_seconds())
func_run_time = datetime.now(timezone.utc)
stored_reminders = store_reminders('reminders.json')
# print('storing reminders', (datetime.now(timezone.utc) - func_run_time).total_seconds())
func_run_time = datetime.now(timezone.utc)
stored_tasks = store_tasks('all_tm_tasks.json')
# print('storing tasks', (datetime.now(timezone.utc) - func_run_time).total_seconds())
func_run_time = datetime.now(timezone.utc)
tm_tasks = store_active_tasks('tm_tasks.json')
# print('storing active task', (datetime.now(timezone.utc) - func_run_time).total_seconds())
func_run_time = datetime.now(timezone.utc)
replace_inbox_file(inbox_location)
# print('replace inbox file', (datetime.now(timezone.utc) - func_run_time).total_seconds())

def read_vault_note_metadata(working_path):
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

    # create excel file placeholder if not exists
    if not os.path.exists(dashboard_location):
        with open(dashboard_location, 'w') as f:
                f.write('done')
        print('made placeholder file. Please paste the excel dashboard excel file from github to the app loacation.')
        
    # check if dashboard location exists 
    if open_excel:
        os.system(fr'start excel "{dashboard_location}"')
    
    # notify of vault read time
    vault_read_end_time = datetime.now(timezone.utc)
    read_time = round((vault_read_end_time - vault_read_start_time).total_seconds() / 60, 2)

    # print(f'Done: Reading Notes In {read_time} min.')
    return notes_nm_task, nm_tasks_keys

def push_notes_to_todos(working_path, app_sync_logic, tm_sync_type='batch'):
    """
    Push notes to todo manager. If file is provided the whole vault will be pushed with recent changes.

    """
    app_sync_logic = app_sync_logic or sync_logic
    current_run_time = datetime.now(timezone.utc)
    
    # read vault notes
    notes_nm_task, nm_tasks_keys = read_vault_notes(working_path)

    # submit task to todoist
    synced_tasks = batch_sync_task_to_tm(notes_nm_task, nm_tasks_keys, current_run_time, app_sync_logic)
    with open(os.path.join(app_location, 'synced_tasks.json'), 'w') as f:
        json.dump(synced_tasks, f)

    # move all archived beacon projects to archive in todo manager if they are active projects
    archived_task = batch_archive_projects(working_path, stored_projects)
        
    print(f'Pushed Notes To Todos: synced {len(synced_tasks)} tasks')
    print(f'Pushed Notes To Todos: archived {len(archived_task)} projects')
    return synced_tasks

def push_todos_to_notes():
    """
    Pull projects from todo manager and updates note manager with latest data.

    """
    # read metadata from vault notes
    notes_metadata = read_vault_note_metadata(vault_location)

    # apply the tm_project_ids for each beacon path
    tm_project_beacons = store_project_beacons(notes_metadata, stored_projects)
    
    # read vault notes
    notes_nm_task, nm_tasks_keys = read_vault_notes(vault_location)

    # create an object of recurring task
    recurring_nm_tasks = unpack_nm_note_task(notes_nm_task=notes_nm_task, task_type='recurring')
    missing_recurring_completions = get_missing_recurring_completions(recurring_nm_tasks)

    # write todo manger to obsidian
    all_tasks_processed = writeback_td_task_to_nm(tm_tasks, missing_recurring_completions, notes_nm_task, tm_project_beacons)
    return tm_tasks

def sync_notes(working_path):
    """
    Push notes to todo manager. If file is provided the whole vault will be pushed with recent changes.

    """
    # get last vault sync time
    try:
        with open(os.path.join(app_location, 'app.json'), 'r') as f:
            app_data = json.load(f)
        last_sync_timestamp = app_data['notes_sync_timestamp']
    except:
        # file does not exists, create file and lookback for changes 30 days.
        app_data = {}
        notes_sync_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
        last_sync_timestamp = str(notes_sync_timestamp - timedelta(days=30))
        app_data['notes_sync_timestamp'] = str(last_sync_timestamp)
        app_data['notes_sync_timestamp_local'] = str(datetime.now())
        with open(os.path.join(app_location, 'app.json'), 'w') as f:
            json.dump(app_data, f)
    
    # current timestamp
    current_run_time = datetime.now(timezone.utc)
    
    # pull the latest changes from todo manager
    func_run_time = datetime.now(timezone.utc)
    tm_changes_since_last_sync = get_last_activity_since_timestamp(last_sync_timestamp=last_sync_timestamp)

    # read metadata from vault notes
    func_run_time = datetime.now(timezone.utc)
    notes_metadata = read_vault_note_metadata(vault_location)
    # print('read vault note metadata:', (datetime.now(timezone.utc) - func_run_time).total_seconds())
    # apply the tm_project_ids for each beacon path
    func_run_time = datetime.now(timezone.utc)
    tm_project_beacons = store_project_beacons(notes_metadata, stored_projects)
    # print('store project beacons:', (datetime.now(timezone.utc) - func_run_time).total_seconds())

    # read vault notes
    func_run_time = datetime.now(timezone.utc)
    notes_nm_task, nm_tasks_keys = read_vault_notes(working_path)
    # print('read_vault_notes', (datetime.now(timezone.utc) - func_run_time).total_seconds())

    # create an object of recurring task
    func_run_time = datetime.now(timezone.utc)
    recurring_nm_tasks = unpack_nm_note_task(notes_nm_task=notes_nm_task, task_type='recurring')
    # print('unpack_nm_note_task', (datetime.now(timezone.utc) - func_run_time).total_seconds())
    func_run_time = datetime.now(timezone.utc)
    missing_recurring_completions = get_missing_recurring_completions(recurring_nm_tasks)
    # print('get missing recurring completions', (datetime.now(timezone.utc) - func_run_time).total_seconds())

    # update notes with any changes that are in todoist
    # write todo manger to obsidian
    func_run_time = datetime.now(timezone.utc)
    tm_new_task_for_beacon, created_recurring_completed_task = writeback_since_sync_to_nm(tm_tasks, missing_recurring_completions, notes_nm_task, tm_project_beacons, tm_changes_since_last_sync)
    with open(os.path.join(app_location, 'tm_task_changes_since_last_sync.json'), 'w') as f:
        json.dump(tm_changes_since_last_sync, f)
    # print('writeback since sync to notes', (datetime.now(timezone.utc) - func_run_time).total_seconds())

    # submit task to todoist
    func_run_time = datetime.now(timezone.utc)
    date_format = "%Y-%m-%d %H:%M:%S.%f%z"
    last_sync_timestamp = datetime.strptime(last_sync_timestamp, date_format).replace(tzinfo=timezone.utc)
    sync_logic['sync_app_timestamp'] = last_sync_timestamp # include setting to sync based on last run of this sync function
    synced_tasks = batch_sync_task_to_tm(notes_nm_task, nm_tasks_keys, current_run_time, sync_logic=sync_logic)
    with open(os.path.join(app_location, 'synced_tasks.json'), 'w') as f:
        json.dump(synced_tasks, f)
    # print('batch sync task to todo manager', (datetime.now(timezone.utc) - func_run_time).total_seconds())

    # create new task into their beacon pages
    writeback_new_task_lines_to_nm(tm_new_task_for_beacon, created_recurring_completed_task)

    # move all archived beacon projects to archive in todo manager if they are active projects
    func_run_time = datetime.now(timezone.utc)
    archived_task = batch_archive_projects(working_path, stored_projects, notes_metadata)
    # print('batch archive projects', (datetime.now(timezone.utc) - func_run_time).total_seconds())
        
    # save the updated timestamp time
    notes_sync_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
    app_data['notes_sync_timestamp'] = str(notes_sync_timestamp)
    app_data['notes_sync_timestamp_local'] = str(datetime.now())

    with open(os.path.join(app_location, 'app.json'), 'w') as f:
        json.dump(app_data, f)

    # update information on sync:
    print(f'Sync Notes: Synced Todo Manager Changes: {len(tm_changes_since_last_sync)} tasks')
    print(f'Sync Notes: Synced Note Manager Changes: {len(synced_tasks)} tasks')
    print(f'Sync Notes: Archived Projects: {len(archived_task)} projects')
    
    return None

def main():
    # add command line arguments
    parser = argparse.ArgumentParser('obsidian todoist inline sync')
    parser.add_argument('--app_action', choices=['read_notes_metadata', 'read_notes', 'push_notes', 'push_todos', 'sync_notes'], help='Action to perform from app.')
    parser.add_argument('--app_working_path', type=str, help='Path to read files from, by default will read the whole vault.', default=vault_location)
    parser.add_argument('--app_sync_logic', type=str, help='Logic for how far back to sync files in the vault.', default=None)
    parser.add_argument('--app_open_excel', type=str, help='Open excel file after reading vault.', default=False)

    args = parser.parse_args()

    action = args.app_action
    working_path = args.app_working_path
    open_excel = args.app_open_excel
    app_sync_logic = args.app_sync_logic
    if app_sync_logic:
        app_sync_logic = json.loads(app_sync_logic.replace("'", '"'))
        
    if action == 'read_notes_metadata':
        read_vault_note_metadata(working_path) # really only used an internal command, but can be used to update namespace
    elif action == 'read_notes':
        read_vault_notes(working_path, open_excel=open_excel)
    elif action == 'sync_notes':
        sync_notes(working_path)
    elif action == 'push_notes':
        push_notes_to_todos(working_path, app_sync_logic)
    elif action == 'push_todos':
        push_todos_to_notes()
    else:
        print('Invalid action specified. Please choose one of: read_notes_metadata, read_notes, push_notes, push_todos')

    
if __name__ == '__main__':
    main()
