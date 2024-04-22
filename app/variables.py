from collections import OrderedDict
import os


# app date sync logic
# sync logic type - 
# frontmatter - prioritize frontmatter datetime followed by file datetime
# file - prioritize frontmatter datetime followed by file datetime
sync_logic = {
    'sync_types': ['file', 'frontmatter'],
    'sync_unit': 'minute', # only handle minutes
    'sync_period': (20),
}

# app folder locations
dashboard_location = r"G:\My Drive\Projects\Coding Projects\obsidian-todoist-task-sync\app\dashboard.xlsx"
vault_location = 'test_vault'
fslash_vault_location = (vault_location.rstrip(r'/') + r'/').replace('\\', r'/')
app_location = os.path.join('_obsidian', 'todist-inline_sync') # app folder created for the application to store data
app_location = os.path.join(vault_location, app_location)
inbox_location = os.path.join(vault_location, 'inbox', 'inbox.md') # dropoff file for new task from todo manager
namespace_location = os.path.join(vault_location, 'inbox', 'todo_namespace.md') # file to store 

# app todoist data location (no need to change)
app_tasks_location = os.path.join(app_location, 'tasks.md')
app_projects_location = os.path.join(app_location, 'projects.json')
app_routines_location = os.path.join(app_location, 'routines.md')

# frontmatter variables 
frontmatter_modified_date_field = 'file_mtime'
frontmatter_modified_date_regex = r'(\d{4}-\d{2}-\d{2}(?: \d{1,2}:\d{1,2})?)'
frontmatter_modified_date_format = "%Y-%m-%d %H:%M %z"

# parsing variables (no need to change)
task_identifier_pattern = '^[ \t]*(?:[-*+]|(?:\d*\.))\s\[.{1}\]'

# task_meta_dates 
user_add_created_date_to_all_task_without_it = True
# user_defined_extraction_regex 
# following these patterns will create a field in the dashboard excel file for filtering
user_task_extraction_regexes = {
    'duration': {
        'regex_name': 'duration',
        'regex': '.*⏲️ ([0-9][0-9]?:[0-9][0-9]?)',
        'data_type':'string', # defaults to string - otherwise choose between ('int', 'float', 'date')
    },
}

# Starting from the left, upon hitting any one of these characters the name of the task 
# will be determined to be everything to the left of the character
# Ex. Task = "- [ ] Review emails #todo 📅 2000-01-01"
# Ex. Task_name = Review emails
# (no need to change)
task_starter_chars = {
    '#': 'label',
    '[Todoist]': 'todo_manager',
    '🔔': 'reminder_submitted',
    '⏰': 'reminder_date',
    '📅': 'due_date',
    '⏳': 'scheduled_date',
    '🛫': 'start_date',
    '✅': 'completed_date',
    '➕': 'created_date',
    '🔺': 'highest_priority',
    '⏫': 'high_priority',
    '🔼': 'medium_priority', 
    '🔽': 'low_priority',
    '⏬': 'lowest_priority',
    '🔁': 'recurrence',
}
task_starter_chars_swapped = {value: key for key, value in task_starter_chars.items()}

# Definition for what priorities markers mean, (no need to change)
tm_priority_names = {
    '🔺': 'highest',
    '⏫': 'high',
    '🔼': 'medium',
    '🔽': 'low',
    '⏬': 'lowest', 
}

# Mapping for how the todo manager will interpret priority
# these are to be user configured. 
# WARNING: a p4 value is the default todoist priroity. Any emoji mapped to this value will be placed back to the note manger even
    # if not entered in the note manager
# NOTE: For mappings that repeat a priority-p-value, the last icon being used for that p-value will be the emoji that is used.
tm_priority_to_nm_priority_mapping = {
    '🔺': 'p1',
    '⏫': 'p2',
    '🔼': 'p3',
    '🔽': 'p5',
    '⏬': 'p6',
}
tm_priority_to_nm_priority_mapping_swapped = {value: key for key, value in tm_priority_to_nm_priority_mapping.items()}

# Todo manager task identifiers
# (no need to change)
tm_task_date_signals = r'⏰📅⏳🛫✅➕'
tm_task_priority_signals = r'🔺⏫🔼🔽⏬'
tm_task_recurrence_signals = r'🔁'
tm_http_link = 'https://todoist.com/showTask?id='

# Header pattern - Used to determine under what markdown header to store new
# task under coming from todo manager.
header_pattern_name = 'To Do'
header_pattern = fr'^##\s({header_pattern_name})$'
general_header_pattern = fr'^(##\s.*)'

# Todo tags - these are normal tags applied to task in todo manger. If a tag is in this list
# it will be prefixed with #Todo/. This is to provide a namespace for task.
td_todo_prefix = 'todo'
td_todo_tags = [
    # context
    'computer',
    'home',
    'errands',
    # mood
    'quick_hits',
    'focus_work',
    'hanging_around',
    'calls_text',
    # time
        # none
    #  priority
    'focus',
    'wor_from_me'
    'wor',
    # status
    'next',
    'repeat',
    # routines
    'repeat_duty',
    'repeat_habit',
    'repeat_chore',
    'repeat_paused',
]

# The app will not send off any task in these directories to the todo manager.
# nm_capture_pattern = 
    # - Regex path for excluding task from being submitted to todo manager
#  nm_ignore_path_from_task_parsing = 
    # - Will exclude this path for the program to stop it from parsing anything in the file.
nm_exclusion_folder_paths = {
    'Archive': {
        'nm_capture_pattern':f'(?i){fslash_vault_location}/4 Archive/.*',
        'nm_ignore_path_from_task_parsing': False,
        'nm_is_archive_folder': True
    },
    'Obisidian Trash': {
        'nm_capture_pattern':f'(?i){fslash_vault_location}/\.trash/.*',
        'nm_ignore_path_from_task_parsing': True
    },
}

# These are regex paths that define where in the todo manger to place any new task created in the note manager.
nm_to_tm_folders_mapping = OrderedDict()
nm_to_tm_folders_mapping = {
    'Projects': {                                    # description of rule
        'nm_capture_pattern': '(?i)1 Projects/.*',   # regex path rule applies to
        'nm_folder_path': '(?i)1 Projects/([^/]*)',  # regex to pull the folder name from. In this case the next folder.
        # ex. captured_path= "1 Projects/create app/ideas/tasks.md"
            # {nm_folder} = "create app"
            # tm_folder = "Projects/create app"
        'tm_folder_path': 'Projects/{nm_folder_path}',  # location in tm, can use the path name pulled from nm_folder_path or hardcode one.
    },
    'Areas': {
        'nm_capture_pattern':'(?i)2 Areas/.*',
        'nm_folder_path':'(?i)2 Areas/([^/]*)',
        'tm_folder_path':'Areas/{nm_folder_path}',
    },
    'General Somedays': {
        'nm_capture_pattern':'(?i)3 Resources/0 Someday-Interest/0 Someday',
        'tm_folder_path':'Someday/General Someday',
    },
    'Somedays': {
        'nm_capture_pattern':'(?i)3 Resources/0 Someday-Interest/.*',
        'nm_folder_path':'(?i)3 Resources/0 Someday-Interest/([^/]*)',
        'tm_folder_path':'Someday/{nm_folder_path}',
    },
    'Somedays All': {
        'nm_capture_pattern':'(?i)3 Resources/.*',
        'tm_folder_path':'Someday/Someday',
    },
    'testing more': {
        'nm_capture_pattern':'(?i)testing/.*',
        'nm_folder_path':'(?i)testing/([^/]*)', #TODO:FIX: this is capturing the note as well. And creating a project from it. So need to add logic to ignore notes.
        'tm_folder_path':'testing/{nm_folder_path}',
    },
    'testing': {
        'nm_capture_pattern':'(?i)testing/.*',
        'tm_folder_path':'someday/someday',
    },
}
 
# These status are used to determine how the app handles any task. 
# In general open task are pushed to the todo manager. Others are not.
# open, cancel, delete, close, ignore
# (no need to change)
task_status_types = {
    # status_type: checkbox_status
    'todo': 'open',
    'in_progress': 'open',
    'cancelled': 'cancel',
    'deleted': 'delete',
    'done': 'close',
    'non_task': 'ignore',
}

# These define how to interpret the characters inside the task box [ ].
task_checkbox_statuses = {
    # representation in task -> [ ] -> Todo
    " ": {
        "task_status_type": "todo",
        "task_status_symbol": " ",
        "task_status_name": "Todo",
        "task_next_status_symbol": "x",
    },
    "x": {
        "task_status_type": "done",
        "task_status_symbol": "x",
        "task_status_name": "Done",
        "task_next_status_symbol": " ",
    },
    "X": {
        "task_status_type": "done",
        "task_status_symbol": "X",
        "task_status_name": "Checked",
        "task_next_status_symbol": " "
    },
    "/": {
        "task_status_type": "in_progress",
        "task_status_symbol": "/",
        "task_status_name": "In Progress",
        "task_next_status_symbol": "x"
    }, 
    "-": {
        "task_status_type": "cancelled",
        "task_status_symbol": "-",
        "task_status_name": "Cancelled",
        "task_next_status_symbol": " "
    },
    "_": {
        "task_status_type": "deleted",
        "task_status_symbol": "_",
        "task_status_name": "Deleted",
        "task_next_status_symbol": "_"
    },
    ">": {
        "task_status_type": "todo",
        "task_status_symbol": ">",
        "task_status_name": "Rescheduled",
        "task_next_status_symbol": "x"
    },
    "<": {
        "task_status_type": "todo",
        "task_status_symbol": "<",
        "task_status_name": "Scheduled",
        "task_next_status_symbol": "x"
    }, 
    "!": {
        "task_status_type": "todo",
        "task_status_symbol": "!",
        "task_status_name": "Important",
        "task_next_status_symbol": "x"
    },
    "?": {
        "task_status_type": "todo",
        "task_status_symbol": "?",
        "task_status_name": "Question",
        "task_next_status_symbol": "x"
    },
    "*": {
        "task_status_type": "todo",
        "task_status_symbol": "*",
        "task_status_name": "Star",
        "task_next_status_symbol": "x"
    },
    "n": {
        "task_status_type": "todo",
        "task_status_symbol": "n",
        "task_status_name": "Note",
        "task_next_status_symbol": "x"
    },
    "l": {
        "task_status_type": "todo",
        "task_status_symbol": "l",
        "task_status_name": "Location",
        "task_next_status_symbol": "x"
    },
    "i": {
        "task_status_type": "todo",
        "task_status_symbol": "i",
        "task_status_name": "Information",
        "task_next_status_symbol": "x"
    },
    "I": {
        "task_status_type": "todo",
        "task_status_symbol": "I",
        "task_status_name": "Idea",
        "task_next_status_symbol": "x"
    },
    "S": {
        "task_status_type": "todo",
        "task_status_symbol": "S",
        "task_status_name": "Amount",
        "task_next_status_symbol": "x"
    },
    "p": {
        "task_status_type": "todo",
        "task_status_symbol": "p",
        "task_status_name": "Pro",
        "task_next_status_symbol": "x"
    },
    "c": {
        "task_status_type": "todo",
        "task_status_symbol": "c",
        "task_status_name": "Con",
        "task_next_status_symbol": "x"
    },
    "b": {
        "task_status_type": "non_task",
        "task_status_symbol": "b",
        "task_status_name": "Bookmark",
        "task_next_status_symbol": "b"
    },
    "\"": {
        "task_status_type": "todo",
        "task_status_symbol": "\"",
        "task_status_name": "Quote",
        "task_next_status_symbol": "x"
    },
    "0": {
        "task_status_type": "non_task",
        "task_status_symbol": "0",
        "task_status_name": "Speech bubble 0",
        "task_next_status_symbol": "0"
    },
    "1": {
        "task_status_type": "non_task",
        "task_status_symbol": "1",
        "task_status_name": "Speech bubble 1",
        "task_next_status_symbol": "1"
    },
    "2": {
        "task_status_type": "non_task",
        "task_status_symbol": "2",
        "task_status_name": "Speech bubble 2",
        "task_next_status_symbol": "2"
    },
    "3": {
        "task_status_type": "non_task",
        "task_status_symbol": "3",
        "task_status_name": "Speech bubble 3",
        "task_next_status_symbol": "3"
    },
    "4": {
        "task_status_type": "non_task",
        "task_status_symbol": "4",
        "task_status_name": "Speech bubble 4",
        "task_next_status_symbol": "4"
    },
    "5": {
        "task_status_type": "non_task",
        "task_status_symbol": "5",
        "task_status_name": "Speech bubble 5",
        "task_next_status_symbol": "5"
    },
    "6": {
        "task_status_type": "non_task",
        "task_status_symbol": "6",
        "task_status_name": "Speech bubble 6",
        "task_next_status_symbol": "6"
    },
    "7": {
        "task_status_type": "non_task",
        "task_status_symbol": "7",
        "task_status_name": "Speech bubble 7",
        "task_next_status_symbol": "7"
    },
    "8": {
        "task_status_type": "non_task",
        "task_status_symbol": "8",
        "task_status_name": "Speech bubble 8",
        "task_next_status_symbol": "8"
    },
    "9": {
        "task_status_type": "non_task",
        "task_status_symbol": "9",
        "task_status_name": "Speech bubble 9",
        "task_next_status_symbol": "9"
    },
}

# overwrite variables defined here with user variables
from user_variables import *
