import os
import json
from variables import app_location


def store_project_beacons(notes_metadata:dict, stored_projects:dict):
    # apply the tm_project_ids for each beacon path
    tm_project_beacons = {}
    for note, note_dict in notes_metadata.items():
        tm_project_name_path = note_dict.get('note_frontmatter_properties').get('tm_beacon')
        if tm_project_name_path:
            tm_project_name = tm_project_name_path.split("/")[-1]
        else:
            tm_project_name = None
        # grab the project_id from todoist
        found_tm_project = stored_projects.get('name_based').get(tm_project_name)
        if found_tm_project:
            note_dict['note_tm_beacon_project_id'] = stored_projects.get('name_based').get(tm_project_name).get('id')
            tm_project_beacons[found_tm_project.get('id')] = note
    
    with open(os.path.join(app_location, 'tm_project_beacons.json'), 'w') as f:
        json.dump(tm_project_beacons, f)

    return tm_project_beacons