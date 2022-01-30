FROM ubuntu:20.04

RUN apt-get update

# get dependencies
RUN apt install python3-pip python-is-python3 -y && \
    pip install selenium requests webdriver-manager --upgrade

# copy project files
COPY ./src /app

# CMD ["python3", "/app/flanco_scrape.py"]
ENTRYPOINT ["python3", "/app/flanco_scrape.py"]
