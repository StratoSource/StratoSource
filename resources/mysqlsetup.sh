
mysql -u root  <<'SQL'

create database stratosource;
create user 'stratosource'@'localhost' identified by 'stratosource';
create user 'stratosource'@'%' identified by 'stratosource';
grant all on stratosource.* to 'stratosource'@'localhost' with grant option;
flush privileges;
SQL

cd /usr/django/stratosource
python manage.py syncdb --noinput
python manage.py shell < setup.py
