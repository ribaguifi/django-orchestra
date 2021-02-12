FROM python:3.6

RUN apt-get -y update
RUN pip3 install wheel

RUN apt-get -y install python3-dev

RUN apt-get install -y bind9utils ca-certificates gettext libcrack2-dev libxml2-dev\
    libxslt1-dev ssh-client wget xvfb zlib1g-dev git iceweasel dnsutils postgresql-contrib\
    curl sudo vim libgirepository1.0-dev

RUN apt-get clean

RUN useradd orchestra --shell /bin/bash && \
    { echo "orchestra:orchestra" | chpasswd; } && \
    mkhomedir_helper orchestra && \
    adduser orchestra sudo

# RUN echo 'EXPORT $PATH="$PATH:/home/orchestra/.local/bin/"' > /home/orchestra/.bashrc
# RUN git clone https://github.com/ribaguifi/django-orchestra.git
# RUN orchestra-admin startproject panel
# RUN python3 panel/manage.py migrate
# RUN python3 panel/manage.py runserver

# install wkhtmltox
RUN apt-get install -y xfonts-75dpi
RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb -O /tmp/wkhtmltox.deb
RUN dpkg -i /tmp/wkhtmltox.deb

RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.29.0/geckodriver-v0.29.0-linux64.tar.gz -O /tmp/geckodriver.tar.gz
RUN tar -xf /tmp/geckodriver.tar.gz -C /usr/local/bin/

# install orchestra requirements
RUN pip3 install --upgrade pip

# TODO(@slamora): requirements.txt duplicates ../totaL_requirements.txt
#   Docker compose security policy forbiddes access to parent folders
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

EXPOSE 8000
