FROM debian:stable-slim

RUN apt-get -y update && apt-get install -y curl sudo git python3 python3-pip
RUN pip3 install -r https://raw.githubusercontent.com/ribaguifi/django-orchestra/master/requirements.txt
RUN useradd orchestra --shell /bin/bash && { echo "orchestra:orchestra" | chpasswd; } && mkhomedir_helper orchestra && adduser orchestra sudo
RUN echo 'EXPORT  $PATH="$PATH:/home/orchestra/.local/bin/"' > /home/orchestra/.bashrc
RUN apt-get clean

WORKDIR /home/orchestra
COPY . .

RUN pip3 install -r requirements.txt
RUN pip3 install -e .

USER orchestra
RUN orchestra-admin startproject panel

ENTRYPOINT ["sh", "-c", "tail -f /dev/null"]