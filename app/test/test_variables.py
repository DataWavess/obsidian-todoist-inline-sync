from variables import *

# date_icon_pattern = f"(\[⏰📅⏳🛫✅➕\]) (\d{{4}}-\d{{2}}-\d{{2}}(?: (?:[0-2]?[0-9]:[0-5]?[0-9])))"
input = '- [ ] task starting with a plus sign ⏬ ⏰ 2023-10-01 [Todoist](https://todoist.com/showTask?id=7338318330)'
input = '- [ ] task starting with a plus sign ⏬ ⏰ 2023-10-01  [Todoist](https://todoist.com/showTask?id=7338318330)'
date_icon_pattern = f"([{tm_task_date_signals}]) (\d{{4}}-\d{{2}}-\d{{2}}(?: (?:[0-2]?[0-9]:[0-5]?[0-9]))?)"

print('date icon pattern', date_icon_pattern)
date_pairs = re.findall(date_icon_pattern, input)
print('date icon pattern', date_pairs)

# UTILITY: get example of the icons in checkbox statuses
# for k, v in task_checkbox_statuses.items():
#     task_name = v.get('task_status_name')
#     task_type = v.get('task_status_type')
#     # print(k, v.get('task_status_name'))
#     x = f'["&{task_name}", (*) => ReplaceTextWith("{k}")],'
#     x = f'- [{k}] {task_name} : classified as {task_type}'
#     print(x)
