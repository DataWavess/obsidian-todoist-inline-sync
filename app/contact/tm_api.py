from todoist_api_python.api_async import TodoistAPIAsync
from todoist_api_python.api import TodoistAPI
import requests
import uuid
from datetime import datetime, timezone
import os
import json
from variables import app_location

try:
    from variables import API_KEY
    api = TodoistAPI(API_KEY)
    api_sync = TodoistAPIAsync(API_KEY)
except:
    api = TodoistAPI(API_KEY)
    api_sync = TodoistAPIAsync(API_KEY)

# Get activity
def get_activity(object_type:str, page:int, limit:int, offset:int):
    """
    Pulls activity that occured for the given parameters
    - object_type = filters events by a specific object_type. ie. 'item', 'note', 'project
    - page = each page is how many weeks back to pull events
    - limit = the number of evetns to return. Max: 100
    - offset = number of events to skip

    Returns:
    - event activity
    """
    event_type = ['added', 'updated', 'completed', 'uncompleted', 'deleted']
    url = 'https://api.todoist.com/sync/v9/activity/get'
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "object_type": object_type,
        "page": page,
        "limit": limit,
        "offset": offset
    }

    response = requests.post(url=url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()
    return response

def get_last_activity_since_timestamp(last_sync_timestamp:str, tm_object_type:str='item') -> dict:
    """
    Returns the events that have changed since the sync timestamp provdided
    - event_types = ['added', 'updated', 'completed', 'uncompleted', 'deleted']

    Return:
    - dict of todo manager objects, and their associated last event since timestamp
    """
    date_format = "%Y-%m-%d %H:%M:%S.%f%z"
    last_sync_timestamp = datetime.strptime(last_sync_timestamp, date_format).replace(tzinfo=timezone.utc)

    completed_pulling_changes_since_last_push_of_notes = False
    new_events = {}
    object_type, page, limit, offset = tm_object_type, 0, 100, 0
    while not completed_pulling_changes_since_last_push_of_notes:
        # get events to iterate over
        changes_for_period = get_activity(object_type=object_type, page=page, limit=limit, offset=offset)
        events_in_period = changes_for_period.get('events')
        events_count = changes_for_period.get('count')
        changes_since_last_sync = {}
        for event in events_in_period:
            event_timestamp = datetime.fromisoformat(event['event_date'].replace('Z', "+00:00"))
            if event_timestamp > last_sync_timestamp:
                if event['object_id'] not in new_events:
                    new_events[event['object_id']] = {
                        'object_id': event['object_id'],
                        'object_type': event['object_type'],
                        'event_date': event['event_date'],
                        'event_type': event['event_type'],
                        'project_id': event['parent_project_id'],
                        # 'info_events_count': events_count,
                        # 'info_page': page,
                        # 'info_limit': limit,
                        # 'info_offset': offset,
                    }
            else:
                completed_pulling_changes_since_last_push_of_notes = True
                break
            changes_since_last_sync[event.get('id')] = event
        
        if not completed_pulling_changes_since_last_push_of_notes:
            if events_count > limit + offset :
                offset+=limit
            else:
                offset=0
                page+=1
        if events_count == 0:
            break

        with open(os.path.join(app_location, 'tm_task_activity_since_lst_sync.json'), 'w', encoding='utf-8') as file:
            json.dump(changes_since_last_sync, file)

    return new_events


# Get resources
def get_resources(resource: str):
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "sync_token": "*",
        "resource_types": f'["{resource}"]'
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        # Process the response JSON as needed
        print(response_json.get('items'))
    else:
        # Handle the case when the API request fails
        print(f"Failed to make the sync request. Status code: {response.status_code}")

    return 

def get_completed_resources(resource: str):
    """
    Retrieves completions of the given resource.

    Return:
    - 
    """
    url = f"https://api.todoist.com/sync/v9/completed/get_all"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        response_json = response.json()
        # Process the response JSON as needed
        return response_json.get(resource)
    else:
        # Handle the case when the API request fails
        print(f"Failed to make the sync request. Status code: {response.status_code}")

    return 

# Fetch tasks synchronously
def get_tasks_sync():
    try:
        tasks = api.get_tasks()
        return tasks
    except Exception as error:
        print(error)
    return

def get_task_sync(task_id):
    try:
        task = api.get_task(task_id)
        return task
    except Exception as error:
        pass
    return 

# fetch tasks asynchronously
async def get_tasks_async() -> dict:
    """
    Pulls all active task from todo manager

    Returns 
    - dict of tm_task, with id as key of task
    """
    try:
        tasks = await api_sync.get_tasks()
        tm_task = {}
        for task in tasks:
            task = task.to_dict()
            tm_task[task.get('id')] = task
        return tm_task
    except Exception as error:
        print(error)
    return

async def get_task_async(task_id:str):
    try:
        task = await api_sync.get_task(task_id)
        return task
    except Exception as error:
        print(error)
    return

# get projects
async def get_projects_async():
    try:
        projects = await api_sync.get_projects()
        return projects
    except Exception as error:
        print(error)
    return

def get_projects():
    try:
        projects = api.get_projects()
        return projects
    except Exception as error:
        print(error)
    return

def get_project(project_id):
    try:
        projects = api.get_project(str(project_id))
        return projects
    except Exception as error:
        print(error)
    return
        
def get_archived_projects() -> dict:
    url = "https://api.todoist.com/sync/v9/projects/get_archived"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.get(url, headers=headers)
    response = response.json()
    archived_projects = {}
    for project in response:
        archived_projects[project.get('id')] = project
        
    return archived_projects

def unarchive_project(project_id) -> bool:
    # Define the API endpoint and headers
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }

    # Define the data payload
    data = {
        "commands": [
            {
                "type": "project_unarchive",
                "uuid": f"{uuid.uuid4()}",
                "args": {
                    "id": f"{project_id}"
                }
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    try:
        if response.status_code == 200:
            response = response.json()
            return response
    except Exception as error:
        print(error)
        raise Exception("API Error: Unable to unachive provided project_id")
    return

def create_project(project_name: str, parent_project_id=None) -> dict:
    try:
        project = api.add_project(name=project_name, parent_id=parent_project_id)
        return project.__dict__
    except Exception as error:
        
        raise Exception('API Error: Unable to create project')

    return 

# update task information
def todoist_update_task(content, passed_dic) -> dict:
    try:
        task = api.update_task(content, **passed_dic)
        return task
    except Exception as error:
        print(error)
    return

# add task
async def todoist_add_task_async(content, passed_dic):
    try:
        task = await api_sync.add_task(content, **passed_dic)
        return task
    except Exception as error:
        print(error)
    return

def todoist_add_task_sync(content, passed_dic):
    try:
        task = api.add_task(content, **passed_dic)
        return task
    except Exception as error:
        print('error:\n', error)
    return


# complete a task
def todoist_complete_task(task_id):
    try:
        is_success = api.close_task(str(task_id))
    except Exception as error:
        print('error:\n', error)
    return


# create a reminder
def create_reminder(tm_task_id: str, reminder_type, reminder) -> int:
    """
    Creates reminder for provided task_id

    Returns:
    The temp_id given to the reminder created in the todo manager
    """
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    uid = uuid.uuid4()
    data = {
        "commands": [
            {
                "type": "reminder_add",
                "temp_id": "e24ad822-a0df-4b7d-840f-83a5424a484a",
                "uuid": f"{uid}",
                "args": {
                    "item_id": f"{tm_task_id}",
                    "due": {
                        "date": f"{reminder}"
                    },
                    "type": f"{reminder_type}"
                }
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    response = response.json()
    sync_status = response.get('sync_status').get(str(uid))
    try:
        if sync_status == 'ok':
            return int(list(response.get('temp_id_mapping').values())[0])
        else:
            err_message = response.get('sync_status').get(str(uid)).get('error')
            # print(err_message)
            return None
    except Exception as error:
        raise Exception(f"API Error: {err_message}")
    return


# get reminders
def get_reminder_by_id(reminder_id=None, task_id=None) -> dict:
    """
    Pulls by reminders by either the provided reminder_id or task_id
    the provided id type, determines the key of the returned dict.

    Note: Completed reminders have their reminders removed and are thus 
    not ever included in the response.

    Returns:
    - Dict of reminder or reminders
    """
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    data = {
        "sync_token": "*",
        "resource_types": '["reminders"]'
    }

    response = requests.post(url, headers=headers, json=data)
    response = response.json()
    reminders = response.get('reminders')

    # pull reminder based on reminder_id
    reminder = {}
    if reminder_id:
        for reminder_obj in reminders:
            current_reminder_id = reminder_obj.get('id')
            if str(current_reminder_id) == str(reminder_id):
                reminder['id'] = reminder_obj
                break
    # pull reminder based on task_id
    elif task_id:
        for reminder_obj in reminders:
            current_reminder_task_id = reminder_obj.get('item_id')
            if str(current_reminder_task_id) == str(task_id):
                reminder['td_task_id'] = reminder_obj
                break

    # return result 
    try:
        if reminder:
            return reminder
    except Exception as error:
        raise Exception(f"API Error: {error}")
    return None

def get_reminders() -> dict:
    """
    Reminders from completed task or reminders that have occured are 
    not included in the response. Since they have been removed from the task 
    in todoist.
    """
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    data = {
        "sync_token": "*",
        "resource_types": '["reminders"]'
    }

    response = requests.post(url, headers=headers, json=data)
    response = response.json()
    reminders = response.get('reminders')

    # return result 
    try:
        return reminders
    except Exception as error:
        raise Exception(f"API Error: {error}")
    return None


# update a reminder
def update_reminder_by_id(reminder_id, new_reminder_date) -> int:
    """
    Submits update to the reminder_id

    Returns
    - reminder_id if succesfull
    """
    uid = uuid.uuid4()
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    data = {
        "commands": [
            {
                "type": "reminder_update",
                "uuid": f'{uid}',
                "args": {
                    "id": reminder_id,
                    "due": {
                        "date": new_reminder_date
                    }
                }
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    response = response.json()
    try:
        sync_status = response['sync_status'][f'{uid}']
        if sync_status == 'ok':
            return int(reminder_id)
    except Exception as error:
        raise Exception(f"API Error: {error}")
        return None
    return None

# Batch commands
def push_batched_commands(batched_commands: list, desired_key: str = None):
    """
    Submits a batch of commands to todoist with an optional key to use to return a specifc dict from the response.

    Desired_key definitions:
        - sync_status = dict of uuids and their sync status
        - temp_id_mapping - dict of created todoist ids for the resource. However updates do not have the actual resource id.
        - sync_token - the sync token to keep track of
        - full_sync - the type of sync status

    Returns:
    - A dict of the response for submission of the commands
    """
    # creating an item reference it by its temp_id
    # updating an id reference it 
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "commands": batched_commands
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        if desired_key:
            return  response.json().get(desired_key)
        else:
            return response.json()
    else:
        raise Exception("Request failed with status code:", response.status_code)
    return None


def test_batch_async():
    # creating an item reference it by its temp_id
    # updating an id reference it 
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
    "commands": [
        {
            "type": "project_add",
            "temp_id": "0a57a3db-2ff1-4d2d-adf6-12490c13c712",
            "uuid": f"{uuid.uuid4()}",
            "args": {"name": "Shopping List"}
        },
        {
            "type": "item_add",
            "temp_id": "ef3d840e-84c9-4433-9a32-86ae9a1e7d42",
            "uuid": f"{uuid.uuid4()}",
            "args": {'project_id': '0a57a3db-2ff1-4d2d-adf6-12490c13c712', 'priority': 1, 'due': {'date': '2023-11-06', 'string': 'every day'}, 'labels': ['repeat'], 'content': 'test recurrence 1'}
        },
        {
            "type": "item_add",
            "temp_id": "8a23c8cb-1d76-469d-a2c0-80a28b3ea6f6",
            "uuid": f"{uuid.uuid4()}",
            "args": {'project_id': '0a57a3db-2ff1-4d2d-adf6-12490c13c712', 'priority': 2, 'due': {'date': '2023-11-06'}, 'labels': ['repeat'], 'content': 'test recurrence 2'}
        },
        {
            "type": "item_add",
            "temp_id": "bf087eaf-aea9-4cb1-ab57-85188a2d428f",
            "uuid": f"{uuid.uuid4()}",
            "args": {'project_id': '0a57a3db-2ff1-4d2d-adf6-12490c13c712', 'priority': 3, 'due_date': '2023-11-06', 'due_string': 'every day', 'labels': ['repeat'], 'content': 'test recurrence 3'}
        },
    ]
    }
    

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("Request was successful")
        print(response.json())
    else:
        print("Request failed with status code:", response.status_code)


def test_batch_async_detailed():
    # creating an item reference it by its temp_id
    # updating an id reference it 
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
    "sync_token": "3217nHu0WLNuB7udVHigxl5d3x67nTwmTvehvOjDLdU3FttMbqNv_FgwA-EQOF5MNE_jJE0ucfGMXPIa15hAL4br4Ref38hbU10lRKD95z8MbkF5",
    "resource_types": ["projects"],
    "commands": [
        {
            "type": "project_add",
            "temp_id": "24a193a7-46f7-4314-b984-27b707bd2331",
            "uuid": "e23db5ec-2f73-478a-a008-1cb4178d2fd1",
            "args": {"name": "Shopping List"}
        }
    ]
    }
        
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("Request was successful")
        print(response.json())
    else:
        print("Request failed with status code:", response.status_code)

# delete reminder
# def delete_reminder():
    # NOTE: This has been decided not to be added. Untill a format for storing task information away from
    # the tasks originating markdown line is determined.


# test
# print(create_reminder('7341162227', 'absolute', '2023-12-12'))
# print(get_reminder_by_id(task_id=7341162227))
# print(update_reminder_by_id(2517009512, '2023-11-01')) 
# print(get_reminders()) 


# import json
# import asyncio

# tm_task = asyncio.run(get_tasks_async())
# print(tm_task)
# with open('tm_tasks.json', 'w') as f:
#     json.dump(tm_task, f, indent=4)

# print(get_resources('completed_info'))
# print(get_completed_resources('items'))
# test_batch_async()
# test_batch_async_detailed()


# update_uuid = uuid.uuid4()
# print(update_uuid)
# test = [
#         {
#             "type": "project_add",
#             "temp_id": "0a57a3db-2ff1-4d2d-adf6-12490c13c712",
#             "uuid": f"{uuid.uuid4()}",
#             "args": {"name": "Shopping List"}
#         },
#         {
#             "type": "item_add",
#             "temp_id": "ef3d840e-84c9-4433-9a32-86ae9a1e7d42",
#             "uuid": f"{uuid.uuid4()}",
#             "args": {'project_id': '0a57a3db-2ff1-4d2d-adf6-12490c13c712', 'priority': 1, 'due': {'date': '2023-11-06', 'due_string': 'every day'}, 'labels': ['repeat'], 'content': 'test recurrence 1'}
#         },
#         {
#             "type": "item_add",
#             "temp_id": "8a23c8cb-1d76-469d-a2c0-80a28b3ea6f6",
#             "uuid": f"{uuid.uuid4()}",
#             "args": {'project_id': '0a57a3db-2ff1-4d2d-adf6-12490c13c712', 'priority': 2, 'due': {'date': '2023-11-06'}, 'labels': ['repeat'], 'content': 'test recurrence 2'}
#         },
#         {
#             "type": "item_add",
#             "temp_id": "bf087eaf-aea9-4cb1-ab57-85188a2d428f",
#             "uuid": f"{uuid.uuid4()}",
#             "args": {'project_id': '0a57a3db-2ff1-4d2d-adf6-12490c13c712', 'priority': 3, 'due_date': '2023-11-06', 'due_string': 'every day', 'labels': ['repeat'], 'content': 'test recurrence 3'}
#         },
#         {
#             "type": "item_move",
#             "uuid": f"{uuid.uuid4()}",
#             "args": {
#                 "id": "bf087eaf-aea9-4cb1-ab57-85188a2d428f",
#                 "parent_id": "8a23c8cb-1d76-469d-a2c0-80a28b3ea6f6",
#             }
#         },
#         # random other order
#         {
#             "type": "item_add",
#             "temp_id": "8a23c8cb-1d76-469d-a2c0-80a28b364899",
#             "uuid": f"{uuid.uuid4()}",
#             "args": {'project_id': '0a57a3db-2ff1-4d2d-adf6-12490c13c712', 'priority': 2, 'due': {'date': '2023-11-06'}, 'labels': ['repeat'], 'content': 'test rando'}
#         },
#         {
#             "type": "item_move",
#             "uuid": f"{uuid.uuid4()}",
#             "args": {
#                 "id": "bf087eaf-aea9-4cb1-ab57-85188a2d428f",
#                 "project_id": "0a57a3db-2ff1-4d2d-adf6-12490c13c712"
#             }
#         },
        
#     ]

# print(push_batched_commands(test, 'sync_status'))
# print(get_activity(object_type = "item", page = "0", limit = "10", offset = "0"))

# from datetime import timedelta
# import json
# current_run_time = datetime.now(timezone.utc) 
# print(current_run_time)
# current_run_time = datetime.now(timezone.utc) - timedelta(days=20)
# print(current_run_time)

# result = get_last_activity_sicne_timestamp(str(current_run_time))

# with open('test_tm_ids_changed_since_last_sync.json', 'w') as f:
#     json.dump(result, f)

# # count task object types
# task_counts = {}
# for task, info in result.items():
#     event_type = info['event_type']
#     if event_type in task_counts:
#         task_counts[event_type] +=1
#     else:
#         task_counts[event_type] = 1

# # count task_ids
# task_counts = {}
# for task, info in result.items():
#     event_type = info['event_type']
#     if task in task_counts:
#         task_counts[task] +=1
#     else:
#         task_counts[task] = 1

# print(task_counts)