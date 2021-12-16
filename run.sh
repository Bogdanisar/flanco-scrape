#!/bin/bash

docker-compose -f compose.yaml build && docker-compose -f compose.yaml up --abort-on-container-exit