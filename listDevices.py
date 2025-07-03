#!/usr/bin/python
import requests
from prettytable import PrettyTable

# DEFINE VARIABLES
controller_ip = '192.168.200.200' # UNCOMMENT AND EDIT THIS
target_api = 'wm/device/' # UNCOMMENT AND EDIT THIS
headers = {'Content-type': 'application/json','Accept': 'application/json'}
url = f'http://{controller_ip}:8080/{target_api}'
response = requests.get(url=url, headers=headers)

if response.status_code == 200:
    # SUCCESSFUL REQUEST
    print('SUCCESSFUL REQUEST | STATUS: 200')
    data = response.json()
    print(data)
    table = PrettyTable(data[0].keys())
    for row in data:
        table.add_row(row.values())
    print(table)
else:
    # FAILED REQUEST
    print(f'FAILED REQUEST | STATUS: {response.status_code}')
