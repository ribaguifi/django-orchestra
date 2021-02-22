FROM python:3.4

RUN apt-get -y update && apt-get install -y curl sudo

RUN export TERM=xterm; curl -L https://raw.githubusercontent.com/ribaguifi/django-orchestra/dev/github-actions/orchestra/bin/orchestra-admin | bash -s install_requirements

RUN apt-get clean

RUN useradd orchestra --shell /bin/bash && \
    { echo "orchestra:orchestra" | chpasswd; } && \
    mkhomedir_helper orchestra && \
    adduser orchestra sudo
