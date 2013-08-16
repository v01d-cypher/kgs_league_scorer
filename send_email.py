import datetime
import logging
import smtplib
from email.mime.text import MIMEText

logging.basicConfig(
    filename='/var/log/duelgo.log',
    level=logging.INFO,
    datefmt='%Y%m%d %H%M',
    format='%(asctime)s : %(levelname)s %(name)s - %(message)s')

log = logging.getLogger('[Send-Mail]')


def process_email(games):
    table_template = open('table_template.html', 'r').read()

    valid_games_html = []
    for game in games['valid']:
        tt = table_template
        valid_games_html.append(tt.format(**game))

    same_guild_games_html = []
    for game in games['same_guild']:
        tt = table_template
        same_guild_games_html.append(tt.format(**game))

    send(valid_games_html + same_guild_games_html)


def connect():
    gmail_user = 'username@gmail.com'
    gmail_passwd = 'passsword'

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(gmail_user, gmail_passwd)
    return server


def send(data):
    TO = 'to@somewhere.com'
    FROM = 'username@gmail.com'
    SUBJECT = 'KGS - DuelGo Results - {}'.format(datetime.datetime.now().strftime('%m/%d/%Y %I:%M %p'))

    msg = MIMEText('\n'.join(data), 'html')
    msg['To'] = TO
    msg['From'] = FROM
    msg['Subject'] = SUBJECT

    server = connect()

    try:
        server.sendmail(FROM, [TO], msg.as_string())
        log.info('\t ... sent')
    except:
        log.info('\t ... ERROR sending')

    server.quit()
