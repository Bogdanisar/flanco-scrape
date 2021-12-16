FROM ubuntu:20.04

RUN apt-get update 

#get chromium
# COPY ./chromium-config/debian.list /etc/apt/sources.list.d/debian.list
# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys DCC9EFBF77E11517
# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 648ACFD622F3D138
# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys AA8E81B4331F7F50
# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 112695A0E562B32A
# COPY ./chromium-config/chromium.pref /etc/apt/preferences.d/chromium.pref
# RUN apt install chromium

RUN DEBIAN_FRONTEND=noninteractive apt install chromium-chromedriver -y


# get dependencies
RUN apt install python3-pip cron -y
RUN apt install python-is-python3 -y
RUN pip install selenium --upgrade
RUN pip install webdriver-manager
RUN apt-get install libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 chromium-browser wget -y


# get chrome
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - 
# RUN sh -c 'echo "deb https://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
# RUN apt-get update
# RUN apt-get install google-chrome-stable -y


# copy project files
COPY ./src /app


# CMD ["/bin/bash", "/app/start.sh"]
# CMD ["python3", "/app/flanco_list.py"]
# CMD 
