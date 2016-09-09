
StratoSource is a configuration and release management tool for Salesforce(tm) development.

####Features
* Track code and configuration changes to a sandbox or production.
* Optionally integrate with [Rally](https://www.rallydev.com) or [AgileZen](http://www.agilezen.com) for story population.
* Tag changes to stories, and stories to releases.
* Use the Release Manifest to view all tagged changes for a release.
* Detects when the same config or code item changes across two pending releases and issues warning.
* Releases include list of tasks to be performed manually during a package push.
* Changes are tracked in a git repository.
* Includes integrated cgit to provide git-level change inspection from the browser.
* Export changed/added custom labels to spreadsheet to send to translation vendors.
* and more...

Stratosource does not perform code or config pushes. 




##Stratosource v2 Notes

### KNOWN WORKING CONFIGURATIONS

- Fedora 24 Server
- CentOS 7
- Red Hat Enterprise Linux 7

There is no technical reason why this will not work on other Linux distros. But you will need to manually replicate the RPM installation procedures or build a compatible package (ie. apt).


### QUICK INSTALL

The quickest path to a working installation is a new VM.

1. Create a VM with [CentOS 7](http://isoredirect.centos.org/centos/7/isos/x86_64/CentOS-7-x86_64-Minimal-1511.iso) or [Fedora 24 Server](https://download.fedoraproject.org/pub/fedora/linux/releases/24/Server/x86_64/iso/Fedora-Server-dvd-x86_64-24-1.2.iso). If you use CentOS you also need to install the EPEL package (```yum install epel-release```)
2. Build or download the latest Stratosource RPM.
   a. To build: Clone the git repo. In the home directory run resources/buildrpm.sh.  The RPM will be under latest/
   b. Pre-built: the RPM under latest/ is already built, based on the master branch.
3. Copy the RPM to the new VM.
4. As root, install the RPM on the VM: ```sudo dnf install -y <rpm filename>```
5. Reboot the VM.  IMPORTANT, to disable selinux.
6. Point your browser to https://<vm ip address>
7. Your new MySQL database root account has no password. Please set one now for security.
8. Installation should be complete.

###QUICK CONFIGURATION

1. Select Manage Repositories & Branches.
2. Click Add under Repositories to create your first git repo.
3. Give the repo a name (simple, one word is best). An example is the same of your Salesforce sandbox like fte, stage, qa, prod, etc.
4. Click Add under Branches
5. Fill out the details under each tab and Save.  See example below to run code snapshots every hour and config every 3 hours.


####SAMPLE BRANCH DETAILS

--General Tab--
Local Source Repository: dev
Branch Name: fte0
API Storage: /tmp/sftmp
Salesforce Environment: Text/Sandbox
Salesforce API User: myaccount@mydomain.com.dev
Salesforce API Password: keepguessing
Verify Password: keepguessing
Authentication Token: myauthtoken
Salesforce Pod: cs21
Branch Enabled: check
UI Order: 0
Salesforce Assets: Custom objects and fields

--Code Snapshots Tab--
Code cron enabled: check
Code cron type: Hourly
Code cron interval: 1
Code cron start: 0

--Config Snapshots Tab--
Config cron enabled: check
Config cron type: Hourly
Config cron interval: 3
Config cron start: 15





####Things to avoid
* Do not manually manipulate the git repos.  The software expects their content to be in a specific state and any changes you make could break parsing
* If you need to work with your git data do so on a copy in another directory.   For example, if you check out a hash to a work branch to recover some code and stratosource kicks off a cron job there will be conflicts when it tries to checkout the other branch while you are working.

####Best Practices
#####Deploy to a Virtual Machine
The ideal Stratosource implementation is via a VM. Never deploy and run from your workstation.  The recommended configuration is:

> * CPU count: 2
> * Memory: 2g is sufficient, but 4g recommended
 > * 20g (alternately, you can use 10 for initial setup then put your /var/sfrepo folder on a separate virtual drive)

#####Development Setup
In order to run on your workstation for development/testing purposes:
> * run the included dev_setup.py script to install Python dependencies
> * create a database.
> * create a database user.
> * edit ss2/settings.py and provide your database/user/password settings
> * to create the tables and initial data run ./manage.py migrate

Note that for development purposes you should not enable code or config cron jobs.

#####Repo Copy
If you want to work with your repo content consider pushing it to another repo after each snapshot.  In /usr/django there is a **post_cronjob.sh** script where you can add in any custom process after a snapshot has run. This would be a great place to perform a git push of the /var/sfrepo content to another repo and also serves as a backup.
To do this you would add your remote repo to each stratosource repo under /var/sfrepo you want to push.  Then, add a git push command to post_cronjob.sh.

#####Large Configurations
I don't know about you, but our organization has a massive amount of configuration data (labels, email templates, reports, etc).  If you do not need to snapshot a particular type of content avoid doing so in order to keep the downloads smaller.  Consider only using the following types for snapshots, and add others only as you need them:

>* objects
>* fields
>* labels
>* approval processes
>* workflows
>

#####Scheduling
* If managing multiple branches and scheduled downloads be sure to stagger them so that no 2 are running at any given time.  For example, if you have 2 branches, poc and dev, and you enable code downloads be sure to set one at the top of the hour and the other at 15 after the hour.  Code downloads typically run in under 2 minutes but config, depending on which assets are selected, could take as long as 10 minutes.

* Config downloads should be scheduled to run less frequently than code as they change less frequently during a development cycle.  In addition, they are larger and slower.  A good starting point is to schedule code downloads every hour and config every 4, then lower the intervals as needed.

#####Tagging
It is a good idea to frequently add tags to your git repo.  This is one type of activity you can safely do in your stratosource git repo directory. This is useful for easily locating points in time where certain features are implemented, or just prior to a environment refresh.

