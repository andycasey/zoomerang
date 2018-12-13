sudo apt-get update
sudo apt-get install git vim
git clone https://github.com/andycasey/zoomerang.git
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
source Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
pip install requests pyyaml twilio google-api-python-client oauth2client
sudo chown -R ubuntu:ubuntu /etc/cron.d/
sudo apt-get install nginx
sudo ufw allow 'Nginx HTTP'
systemctl status nginx
sudo chown -R ubuntu:ubuntu /var/www/html/
# Set the time zone correctly
sudo dpkg-reconfigure tzdata

# Now install crontab for scheduler
cp zoomerang/scripts/zoomerang-scheduler /etc/cron.d/zoomerang-scheduler
