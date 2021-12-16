#!/bin/bash

python3 ./flanco_list.py >> flanco_output.txt 2>&1

# crontab -r
# (crontab -l 2>/dev/null; echo "*/5 * * * * flanco_list.py >> flanco_output.txt 2>&1") | crontab -
