
## Experimental Docker support

### Build the image

```
docker build -t ss2 .
```

### Start the container


#### Ports
* **80** - web interface

#### Volumes
* **/var/sfrepo** - Git repositories home directory - where your Salesforce assets will be versioned.  Should initially be empty
* **/var/sftmp** - temporary storage for downloads and processing

#### Environment Variables
* **dbhost** - Required IP address of your MySQL or Postgresql database host
* **dbport** - optional, port of database if not default
* **dbengine** - optional, either mysql or postgresql. Defaults to mysql

#### Running

```
docker run -e "dbhost=your_host_ip" -e "dbport=your_port"  -e "dbengine=your_db_engine"  -v /your/host/tmp:/var/sftmp  -v /your/git/repodir:/var/sfrepo -p your_host_port ss2
```

Example:

````
docker run -e "dbhost=192.168.1.100" -v /tmp:/var/sftmp  -v /mnt/ssrepo:/var/sfrepo -p 8000 ss2
````

This will start a container pointed my my existing MySQL database at 192.168.1.100 using the default port. I'm mapping my host /tmp directory to the container's sftmp and my repository at /mnt/ssrepo to the container's sfrepo.  The container's web server will listen on port 8000.

