- get pip: https://pip.pypa.io/en/stable/installing/
`curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py`
`python get-pip.py`

- install and setup virtualenv: 
`pip install virtualenv`
`virtualenv env`
`source env/bin/activate`

- install dependencies:
`pip install python-telegram-bot`
`pip install PySocks`
`pip install requests`

- get yourself a gitlab authentication token. Create a file `gitlab_token` and paste the token inside

- get yourself a telegram bot via BotFather bot. Create a file `telegram_token` and paste the bot access token inside

- setup a tor socks5 proxy on a port 9150 or just run tor browser

- run:
python bot.py
