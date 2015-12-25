Setup Basic Linux Server
=========
<!-- MarkdownTOC depth=5 -->

- How to access:
- Tasks accomplished
    - Perform Basic Configuration:
    - Secure your sever
    - Install your application
- Details of the tasks
    - Perform Basic Configurations
        - Launch your Virtual Machine with your Udacity account and log in.
        - Create a new user named grader and grant this user sudo permissions.
        - Disable root user
        - Update all currently installed packages.
        - Configure the local timezone to UTC.
    - Secure your Server:
        - Change the SSH port from 22 to 2200
        - Configure the Uncomplicated Firewall (UFW)
    - Install your application:
        - Install and configure Apache to serve a Python mod_wsgi application
        - Install and configure PostgreSQL
            - Do not allow remote connections
            - Create a new user named catalog that has limited permissions to your catalog application database
    - Install git
        - clone and set up your Catalog App project (from your GitHub repository from earlier in the Nanodegree program)
        - Configure and enable virtual host
        - Make `.git` directory not publicly accessible via a browser!
        - Change SQLite to Postgres DB
    - Additional monitoring and upgrades
        - Automatic upgrade with `unattended-upgrades`
        - Monitor repeated unsuccessful attempts with `fail2ban`
        - Monitor status of server with `glances`
- References

<!-- /MarkdownTOC -->

## How to access:

- `ssh -i ~/.ssh/grader.rsa grader@52.10.197.21 -p 2200`
- or `ssh -i ~/.ssh/udacity_key.rsa root@52.10.197.21 -p 2200`

- The complete url of this project is: http://ec2-52-10-197-21.us-west-2.compute.amazonaws.com/

## Tasks accomplished
### Perform Basic Configuration:
- login VM with udacity account
- Create a new user named grader and grant this user sudo permissions. 
- Update all currently installed packages. 
- Configure the local timezone to UTC. 
### Secure your sever
- Change the SSH port from 22 to 2200 
- Config firewall to only allow connections for SSH (port 2200), HTTP (port 80), and NTP (port 123) 
### Install your application
- Install and configure Apache to serve a Python mod_wsgi application 
- Install and configure PostgreSQL 
    + Do not allow remote connections 
    + Create a new user named catalog that has limited permissions to your catalog application database 
- Install git 
    + Clone repo `catalog` from project 3
    + Check `.git` is excluded from public view
    + Config and run application
- Additional monitoring and upgrades
    + Automatic upgrade with `unattended-upgrades`
    + Monitor repeated unsuccessful attempts with `fail2ban`
    + Monitor status of server with `glances`

## Details of the tasks

### Perform Basic Configurations
#### Launch your Virtual Machine with your Udacity account and log in. 
You can manage your virtual server at: https://www.udacity.com/account#!/development_environment 
```sh
ssh -i ~/.ssh/udacity_key.rsa root@52.10.197.21
```

#### Create a new user named grader and grant this user sudo permissions. 
```sh
sudo adduser grader
sudo adduser grader sudo
```
password: udacity (all lower case)

```sh
$ sudo apt-get install finger
finger grader
Login: grader               Name: grader
Directory: /home/grader               Shell: /bin/bash
Never logged in.
No mail.
No Plan.
```

- list all users `cut -d: -f1 /etc/passwd`

If needed, we can change ssh access to allow using password to login:
```sh
sudo nano /etc/ssh/sshd_config
```

Change `PasswordAuthentication` to `yes`. Save and exist, and restart ssh by `service ssh restart`.
Of course this is less secure!

- Authentication using public key encryption
From local machine:`ssh-keygen`
Type password and save in desired location.
In my example I saved at `~/.ssh/grader.rsa`, copy the `~/.ssh/grader.pub` contents

- Install a public key on remote server:
paste the copied contents into `/home/grader/.ssh/authorized_keys`

```sh
chmod 700 .ssh
chmod 644 .ssh/authorized_keys
service ssh restart
```

Now I can login with `ssh -i ~/.ssh/grader.rsa grader@52.10.197.21 -p 2200`

#### Disable root user
1. To allow new users, append to `/etc/ssh/sshd_config` `AllowUsers grader, catalog`.
2. Change `PermitRootLogin no`
3. Add `DenyUsers root`
4. Restart sshd service: `service ssh restart`


#### Update all currently installed packages. 
```sh
sudo apt-get update
sudo apt-get upgrade
```

#### Configure the local timezone to UTC. 
Select none of the above, then UTC
```sh
$ dpkg-reconfigure tzdata

Current default time zone: 'Etc/UTC'
Local time is now:      Tue Dec 22 09:18:49 UTC 2015.
Universal Time is now:  Tue Dec 22 09:18:49 UTC 2015.
```

### Secure your Server:

#### Change the SSH port from 22 to 2200 
Change ssh port number by
```sh
sudo nano /etc/ssh/sshd_config
```
Change `Port` to `2200`. Save and exist, and restart ssh by `service ssh restart`.

After that, login with
```sh
ssh -i ~/.ssh/udacity_key.rsa root@52.10.197.21 -p 2200
```

#### Configure the Uncomplicated Firewall (UFW)
Only allow incoming connections for SSH (port 2200), HTTP (port 80), and NTP (port 123) 

```sh
$ ufw status
Status: inactive
$ ufw default deny incoming
$ ufw default allow outgoing
$ ufw allow ssh
$ ufw allow www
$ ufw allow ntp
$ ufw allow 2200/tcp
$ ufw enable
$ ufw status
Status: active

To                         Action      From
--                         ------      ----
22                         ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
123                        ALLOW       Anywhere
2200/tcp                   ALLOW       Anywhere
22 (v6)                    ALLOW       Anywhere (v6)
80/tcp (v6)                ALLOW       Anywhere (v6)
123 (v6)                   ALLOW       Anywhere (v6)
2200/tcp (v6)              ALLOW       Anywhere (v6)
```

### Install your application:

#### Install and configure Apache to serve a Python mod_wsgi application 
```sh
sudo apt-get install apache2
sudo apt-get install python-setuptools libapache2-mod-wsgi
sudo service apache2 restart
```

#### Install and configure PostgreSQL 
```sh
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install python-psycopg2
sudo -u postgres -i
```

##### Do not allow remote connections 
By default remote connections are not allowed.
Double check by `more /etc/postgresql/9.3/main/pg_hba.conf`

(I removed the comments so they don't show up in TOC)
```
local   all             postgres                                peer
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

##### Create a new user named catalog that has limited permissions to your catalog application database 

```sh
$ sudo -u postgres -i
$ psql
```
or
```sh
$ sudo -u postgres psql

postgres=# \du
                             List of roles
 Role name |                   Attributes                   | Member of
-----------+------------------------------------------------+-----------
 postgres  | Superuser, Create role, Create DB, Replication | {}

postgres=# CREATE ROLE catalog WITH login createdb;
postgres=# \du
                             List of roles
 Role name |                   Attributes                   | Member of
-----------+------------------------------------------------+-----------
 catalog   | Create DB                                      | {}
 postgres  | Superuser, Create role, Create DB, Replication | {}

ALTER ROLE catalog WITH PASSWORD 'udacity';
CREATE DATABASE catalog;
```

### Install git 
`sudo apt-get install git`

#### clone and set up your Catalog App project (from your GitHub repository from earlier in the Nanodegree program)  

```
$ sudo apt-get install python-pip python-dev build-essential
$ sudo pip install --upgrade pip
```

Find server's ip address (not really useful for this task but I thought it's interesting to know)
```sh
$ fconfig eth0 | grep inet | awk '{ print $2  }'
addr:10.20.3.224
addr:
```

Clone the repo, copy to `/var/www/catalog`
`$ git clone https://github.com/prodbuilder/udacity-nano-fullstack.git`

#### Configure and enable virtual host

1. Check ubuntu version
```sh
$ lsb_release -a
No LSB modules are available.
Distributor ID:  Ubuntu
Description:  Ubuntu 14.04.3 LTS
Release:  14.04
Codename:  trusty
```

Add `ServerName localhost` in `/etc/apache2/apach2.conf` 

2. Create and enable a new virtual host
`nano /etc/apache2/sites-available/catalog.conf`
With the content in `/catalog.conf`

Create symbolic link in `sites-enabled` with
```
ln -s /etc/apache2/sites-available/catalog.conf /etc/apache2/sites-enabled/catalog.conf
```
or with `a2ensite catalog.conf`

3. Create the `.wsgi` file

My main repo live in `/var/www/catalog/catalog`. 
I originally had it under `/root/` and ran into `Apache: access denied because search permissions are missing`. Moving the directory out of `/root` solved this.

Copy the `catalog.wsgi` file to `/var/www/udacity-nano-fullstack/catalog.wsgi`

Then `service apache2 restart`

4. Now sever is serving your catalog app at http://ec2-52-10-197-21.us-west-2.compute.amazonaws.com/, but is still configured to server the default apache page at http://52.10.197.21/. To disable the default virtual host, `sudo a2dissite 000-default.conf`.

5. Careful! Disable Flask debug mode in `catalog.py`.

#### Make `.git` directory not publicly accessible via a browser! 

I found 3 potential solutions: 
1. create `.htaccess` file in `.git` directory and put in
```
<Directory .git>
    order allow,deny
    deny from all
</Directory>
```
But if the repo is re cloned, this process would need to be repeated.

2. Alternatively we can `chmod 700 .git`
By default
`drwxr-xr-x 8 root root 4.0K Dec 23 19:56 .git`
After change
`drwx------ 8 root root 4.0K Dec 23 19:56 .git`

3. Copy the repo files into `/var/www`, and this skips the .git directory, which is what I did for this project.


Check that it is not accessible from browser 
Visiting http://ec2-10-20-3-224.us-west-2.compute.amazonaws.com/.git/ should result in 404.

#### Change SQLite to Postgres DB
This involves changing the DB_NAME when creating engine.
For client secret files for G+ and Facebook login, referring to the absolute path.
Add `http://ec2-52-10-197-21.us-west-2.compute.amazonaws.com/` to properly configure third party authentication. 

### Additional monitoring and upgrades

#### Automatic upgrade with `unattended-upgrades`
https://wiki.debian.org/UnattendedUpgrades
`apt-get install unattended-upgrades apt-listchanges`
Edit `/etc/apt/apt.conf.d/50unattended-upgrades` and uncomment `Unattended-Upgrade::Mail "root";`

To activate, `nano /etc/apt/apt.conf.d/20auto-upgrades`
Add the following contents
```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

#### Monitor repeated unsuccessful attempts with `fail2ban`
These links contain excellent information on using `Fail2ban` for `ssh`, `apache` and `nginx`. 
https://www.digitalocean.com/community/tutorials/how-to-protect-ssh-with-fail2ban-on-ubuntu-14-04
http://www.fail2ban.org/wiki/index.php/Downloads

```sh
apt-get install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```
For now, accepting the default.

#### Monitor status of server with `glances`
Install `glances`, a cross-platform curses-based monitoring tool with `pip install glances`.https://nicolargo.github.io/glances/
See results with `glances`.

## References

- [Markedly underwhelming and potentially wrong resource list for P5](https://discussions.udacity.com/t/markedly-underwhelming-and-potentially-wrong-resource-list-for-p5/8587)
- [Project 5 Resources](https://www.google.com/url?q=https://discussions.udacity.com/t/project-5-resources/28343&sa=D&usg=AFQjCNGqcsTV50-bXPCjQ5fkOYzLEdpUZA)
- [P5 How I got through it](https://discussions.udacity.com/t/p5-how-i-got-through-it/15342/15)
