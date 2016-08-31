
mysql -u root  <<'SQL'

create database if not exists stratosource;
create user 'stratosource'@'localhost' identified by 'stratosource';
create user 'stratosource'@'%' identified by 'stratosource';
grant all on stratosource.* to 'stratosource'@'localhost' with grant option;
flush privileges;

SQL

cd /usr/django
python manage.py migrate --run-syncdb --database ss
python manage.py shell < resources/setup.py
