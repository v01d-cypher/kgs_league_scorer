from email.mime.text import MIMEText
import datetime
import logging
import smtplib
import yaml


config = yaml.load(open('config.yaml', 'rb'))

logging.basicConfig(
    filename=config['logfile'],
    level=logging.INFO,
    datefmt='%Y%m%d %H%M',
    format='%(asctime)s : %(levelname)s %(name)s - %(message)s')
log = logging.getLogger('[Send-Mail]')


def process_email(games):
    table_template = open('games_template.html', 'r').read()

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
    server = smtplib.SMTP(config['email_server'], config['email_port'])
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(config['email_login_user'], config['email_login_password'])
    return server


def send(data):
    TO = config['email_to']
    FROM = config['email_from']
    # Add curent date and time to email subject.
    # This helps prevent the emails from landing in a thread in the email client.
    SUBJECT = config['email_subject'] + '- {}'.format(datetime.datetime.now().strftime('%m/%d/%Y %I:%M %p'))

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
