sudo pip3 install -e /code
psql -U orchestra -h postgres < /code/examples/createdb.sql

cd ~
django-admin.py startproject panel --template="/code/orchestra/conf/ribaguifi_template"
cp /code/examples/env.example panel/.env

cd panel
python3 manage.py setupcronbeat
python3 manage.py syncperiodictasks

sudo apt-get install -y rabbitmq-server
sudo python3 manage.py setupcelery --username orchestra

sudo python3 manage.py setuplog

python3 manage.py collectstatic --noinput
sudo apt-get install -y nginx-full uwsgi uwsgi-plugin-python3
sudo python3 manage.py setupnginx --user orchestra

sudo /etc/init.d/rabbitmq-server start
sudo pip uninstall celery
sudo pip install celery
sudo pip uninstall django-celery
sudo pip install django-celery
sudo python3 manage.py startservices


# python3 panel/manage.py migrate
