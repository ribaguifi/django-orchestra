# orchestra environment based on docker-compose

Docker compose environment to develop django-orchestra.

**NOTE**: On web container, volume `/code` contains the source code of the host.

1. Build (or rebuild if any change done) the containers:
```
cd examples/
docker-compose build
```

2. Start the containers:
```
docker-compose up
```

3. Run a bash on `web` container:
```
docker-compose run web bash
```

4. Run on the web docker container the first time:
```
pip3 install -e /code
su - orchestra
bash /code/examples/init_project.sh
```

5. Run tests or do whatever you need:
```
cd panel
python manage.py test --noinput orchestra.contrib.lists.tests.functional_tests.tests.AdminListTest.test_add
```
