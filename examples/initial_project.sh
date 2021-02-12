wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb 
sudo dpkg -i wkhtmltox_0.12.6-1.buster_amd64.deb
wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
sudo tar zxf geckodriver-v0.24.0-linux64.tar.gz -C /usr/local/bin/

sudo /etc/init.d/postgresql start

sudo su - postgres -c 'psql -U postgres < /home/orchestra/examples/createdb.sql'

git clone https://github.com/ribaguifi/django-orchestra
cd django-orchestra
git checkout dev/github-actions
sudo pip3 install --upgrade pip
sudo pip3 install -r total_requirements.txt
sudo pip3 install -e .

django-admin.py startproject panel --template="orchestra/conf/ribaguifi_template"
cp .env.example panel/.env
python3 manage.py migrate
