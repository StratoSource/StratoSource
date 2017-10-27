FROM centos

RUN mkdir /usr/django
COPY . /usr/django/
RUN chmod 777 /usr/django/resources/docker_entry.sh

RUN yum -y install epel-release; yum clean all ;\
yum -y install python python-pip ;\
pip install --upgrade pip ;\
pip install django django-bootstrap3 pyexcelerator pyral tzlocal

RUN yum -y install httpd python-suds python-requests python-memcached python-lxml mod_wsgi MySQL-python wget git cgit unzip

RUN cp /usr/django/resources/httpd.conf /etc/httpd/conf.d/stratosource.conf

VOLUME /var/sfrepo
VOLUME /var/sftmp

ENV CONTAINERIZED=docker

EXPOSE 80

CMD /usr/django/resources/docker_entry.sh
