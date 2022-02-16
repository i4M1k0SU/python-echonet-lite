sudo apt -y install python3-dev python3-pip libfreetype6-dev libjpeg-dev build-essential libopenjp2-7 libtiff5 nginx libatlas-base-dev
pip3 install -r requirements.txt
ls ./nginx/log >/dev/null 2>&1
if [ $? -ne 0 ]; then
    mkdir ./nginx/log
fi
ls ./nginx/tmp >/dev/null 2>&1
if [ $? -ne 0 ]; then
    mkdir ./nginx/tmp
fi
sudo cp ./nginx/default.conf /etc/nginx/conf.d/default.conf
sudo cp ./nginx/uwsgi.service /etc/systemd/system
sudo cp ./sample.service /etc/systemd/system
sudo cp ./config_sample.ini ./config.ini
sudo systemctl enable uwsgi.service
sudo systemctl restart nginx
sudo systemctl restart uwsgi.service
sudo systemctl enable sample.service
sudo systemctl start sample.service
