psql -U orchestra -h postgres < /code/examples/createdb.sql

cd ~
django-admin.py startproject panel --template="/code/orchestra/conf/ribaguifi_template"
cp /code/examples/env.example panel/.env

# python3 panel/manage.py migrate
