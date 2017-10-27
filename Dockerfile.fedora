FROM fedora-python2

RUN mkdir /usr/django
COPY . /usr/django/
RUN chmod 777 /usr/django/resources/docker_entry.sh

RUN dnf install -y httpd python-memcached mod_wsgi MySQL-python wget git cgit unzip && \
    cp /usr/django/resources/httpd.conf /etc/httpd/conf.d/stratosource.conf

VOLUME /var/sfrepo
#VOLUME /var/sftmp

RUN mkdir /var/sftmp && chmod 777 /var/sfrepo /var/sftmp && usermod -a -G root apache

ENV CONTAINERIZED=docker

EXPOSE 80

CMD /usr/django/resources/docker_entry.sh
