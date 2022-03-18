FROM debian:stable-slim

RUN apt-get -y update && apt-get install -y curl sudo git python3 python3-pip python3-setuptools python3-venv --no-install-recommends
RUN python3 -m venv /opt/venv
RUN . /opt/venv/bin/activate && pip install wheel

RUN . /opt/venv/bin/activate && pip3 install -r https://raw.githubusercontent.com/ribaguifi/django-orchestra/master/requirements.txt
RUN useradd orchestra --shell /bin/bash && { echo "orchestra:orchestra" | chpasswd; } && mkhomedir_helper orchestra && adduser orchestra sudo
RUN echo 'EXPORT  $PATH="$PATH:/home/orchestra/.local/bin/"' > /home/orchestra/.bashrc
RUN apt-get clean

WORKDIR /home/orchestra
COPY . .

RUN . /opt/venv/bin/activate && pip install -r requirements.txt
RUN . /opt/venv/bin/activate && pip install -e .

USER orchestra
RUN . /opt/venv/bin/activate && django-admin startproject panel --template="/home/orchestra/orchestra/conf/project_template"

WORKDIR /home/orchestra/panel

RUN . /opt/venv/bin/activate && python manage.py migrate --no-input
RUN export DJANGO_SUPERUSER_PASSWORD=admin && . /opt/venv/bin/activate && python manage.py createsuperuser --username admin --email test@example.org --no-input

EXPOSE 9999

ENTRYPOINT . /opt/venv/bin/activate && python manage.py runserver 0.0.0.0:9999