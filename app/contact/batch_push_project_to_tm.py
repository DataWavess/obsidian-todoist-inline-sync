import os
import json
import uuid
from read.read_vault import read_note_metadata
from variables import app_location
from contact.tm_api import push_batched_commands


def batch_archive_projects(working_path:str, stored_projects: dict, notes_metadata: dict=None) -> dict:
    projects_to_archive = {}
    synced_projects = []
    failed_sync_projects = []
    if not os.path.isfile(working_path):
        if not notes_metadata:
            notes_metadata = read_note_metadata(working_path)
        batched_archive_commands = []
        # iterate over metadata in notes looking for is_archive flag
        for note_name, note in notes_metadata.items():
            is_in_archive = note.get('note_is_in_archive')
            is_beacon_note = note.get('note_tm_beacon')
            if is_in_archive and is_beacon_note:
                project_full_name = note['note_tm_beacon']
                print('note:', note)
                print('project_full_name:', project_full_name)
                project_name = project_full_name.split(r'/')[-1]
                existing_project = stored_projects.get('name_based').get(project_name)
                if existing_project:
                    existing_project_is_archived = existing_project.get('is_archived')
                else:
                    existing_project_is_archived = True # project probably is deleted, if it does not exist
                if not existing_project_is_archived:
                    new_uuid = uuid.uuid4()
                    batch_archive_request = {
                        'type': 'project_archive',
                        'uuid': f'{new_uuid}',
                        'args': {
                            'id': str(existing_project['id'])
                        }
                    }
                    batched_archive_commands.append(batch_archive_request)
                    projects_to_archive[str(new_uuid)] = existing_project

        # submit archive commands
        for i in range(0, len(batched_archive_commands), 100):
            upload_batch = batched_archive_commands[i: i+100]
            push_status_dict = push_batched_commands(upload_batch)
            sync_status_dict = push_status_dict.get('sync_status')
            # store the project status for review if failed in sync
            for uid, sync_status in sync_status_dict.items():
                current_project = projects_to_archive.get(uid)
                current_project['tm_batch_sync_status'] = sync_status
                if sync_status == 'ok':
                    current_project['is_archived'] = True
                    synced_projects.append(current_project)
                else:
                    failed_sync_projects.append(current_project)

        # store the archive projects
        with open(os.path.join(app_location, 'archive_projects.json'), 'w') as f:
            json.dump(synced_projects, f)
        with open(os.path.join(app_location, 'failed_archive_projects.json'), 'w') as f:
            json.dump(failed_sync_projects, f)
        # open failed projects to archive file
        if failed_sync_projects:
            os.system(fr"{os.path.join(app_location, 'failed_archive_projects.json')}")

    return synced_projects
