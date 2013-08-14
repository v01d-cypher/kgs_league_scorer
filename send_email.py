import smtplib
from email.mime.text import MIMEText


def process_email(data):
    table_template = open('table_template.html', 'r').read()

    same_guild_html = []
    for game in data['same_guild']:
        tt = table_template
        same_guild_html.append(tt.format(**game))

    games_html = []
    for game in data['games']:
        tt = table_template
        games_html.append(tt.format(**game))

    send(same_guild_html + games_html)


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
    SUBJECT = 'KGS - DuelGo Results'

    msg = MIMEText('\n'.join(data), 'html')
    msg['To'] = TO
    msg['From'] = FROM
    msg['Subject'] = SUBJECT

    server = connect()

    try:
        server.sendmail(FROM, [TO], msg.as_string())
        print('\t ... sent')
    except:
        print('\t ... ERROR sending')

    server.quit()
