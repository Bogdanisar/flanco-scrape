FROM ubuntu:20.04

RUN apt-get update

# get dependencies
RUN apt install python3-pip cron -y
RUN apt install python-is-python3 -y
RUN pip install selenium --upgrade
RUN pip install requests --upgrade

# copy project files
COPY ./src /app

# CMD ["python3", "/app/flanco_scrape.py"]
ENTRYPOINT ["python3", "/app/flanco_scrape.py"]
