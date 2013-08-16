from bs4 import BeautifulSoup
import datetime
import logging
import pprint
import re
import time
import urllib.request
import yaml

import guild_data
import send_email


logging.basicConfig(filename='/var/log/duelgo.log', level=logging.INFO, datefmt='%Y%m%d %H%M', format='%(asctime)s : %(levelname)s %(name)s - %(message)s')
log = logging.getLogger('[DuelGo]')

def save_games_processed(games_processed):
    yaml.dump(games_processed, open('games_processed.yaml', 'w', encoding='UTF-8'), default_flow_style=False)


def load_games_processed():
    return yaml.load(open('games_processed.yaml', 'rb'))


def load_member_data():
    return yaml.load(open('member_data.yaml', 'rb'))


def save_member_data(member_data):
    yaml_data = {}
    for member, data in member_data.items():
        yaml_data[member] = {
            'Points': data['Points'],
            'Tournament Win/Loss': data['Tournament Win/Loss']
        }
    yaml.dump(yaml_data, open('member_data.yaml', 'w', encoding='UTF-8'), default_flow_style=False)


def get_member_data(member):
    if member in guild_members:
        return guild_members[member]

    return {
        'Guild': 'No Guild',
        'Guild Rank': 'Member',
        'Points': '0',
        'Rank': '-',
        'Tournament Win/Loss': '0/0'}


def calc_points(points, won=False):
    try:
        points = int(points)
    except:
        points = 0

    if won:
        return int(points) + 3
    else:
        return int(points) + 2


def calc_win_loss(win_loss, won=False):
    win, loss = win_loss.split('/')
    try:
        win = int(win)
    except:
        win = 0

    try:
        loss = int(loss)
    except:
        loss = 0

    if won:
        return '{}/{}'.format(win + 1, loss)
    else:
        return '{}/{}'.format(win, loss + 1)


def get_guild_members(guild):
    members = []
    for member in guild_members:
        if member['Guild'] == guild:
            members.append(member)
    return members


log.info('Start processing')
games_processed = load_games_processed()

guild_members = guild_data.get_guild_members()
for member, data in load_member_data().items():
    if member in guild_members:
        guild_members[member].update(data)

games = []

for index, member in enumerate(guild_members):
    log.info('Query User #{}: {}'.format(index + 1, member))
    # www.gokgs.com has a time limit between requests. Don't know how much time yet. 5 seconds seems to work for now.
    time.sleep(5)
    request = urllib.request.Request(
        'http://www.gokgs.com/gameArchives.jsp?user={}'.format(member),
        headers={'Cookie': 'timeZone="Africa/Johannesburg"'})
    games_raw = urllib.request.urlopen(request)
    games_soup = BeautifulSoup(games_raw.read())

    for game in games_soup.table.find_all('tr')[1:]:
        tds = game.find_all('td')

        game_viewable = tds[0].text
        game_setup = tds[3].text.strip()
        game_type = tds[-2].text

        # This will also work where user played no games as game_viewable will be a 'Year' from the other table
        if game_viewable == 'Yes' and game_type in ['Free', 'Ranked'] and game_setup.find('19×19') > -1:
            date = datetime.datetime.strptime(tds[4].text.strip(), '%m/%d/%y %I:%M %p')
            game_link = tds[0].a.get('href')

            # only get games played for this date that we haven't processed yet
            if date.date() == datetime.datetime.now().date() - datetime.timedelta(1) and game_link not in games_processed:
                players = {
                    'W': {
                        'name': re.sub(r'(.*)\[.*', r'\1', tds[1].text).strip(),
                        'colour': 'White'
                    },
                    'B': {
                        'name': re.sub(r'(.*)\[.*', r'\1', tds[2].text).strip(),
                        'colour': 'Black'
                    }}

                w_colour = 'B'
                o_colour = 'W'
                result = tds[6].text.strip()

                if result[0] != w_colour:
                    w_colour, o_colour = o_colour, w_colour

                game_data = {
                    'Link': game_link,
                    'Winner': players[w_colour]['name'],
                    'WinnerColour': players[w_colour]['colour'],
                    'Opponent': players[o_colour]['name'],
                    'OpponentColour': players[o_colour]['colour'],
                    'DatePlayed': date.date().strftime('%m/%d/%Y'),
                    'Result': result,
                }
                games.append(game_data)

                games_processed.append(game_link)
                save_games_processed(games_processed)


valid_games = []
same_guild_games = []

for index, game in enumerate(games):
    log.info('Retrieve Game #{}: {}'.format(index + 1, game['Link']))
    # www.gokgs.com has a time limit between requests. Don't know how much time yet. 5 seconds seems to work for now.
    time.sleep(5)
    sgf_data = str(urllib.request.urlopen(game['Link']).read()).lower()
    if sgf_data.find('duelgo') > -1 or sgf_data.find('duel go') > -1:
        game['TableHeader'] = 'Game - {} vs. {}'.format(game['Winner'], game['Opponent'])

        winner_data = get_member_data(game['Winner'])
        opponent_data = get_member_data(game['Opponent'])

        game['WinnerGuild'] = winner_data['Guild']
        game['WinnerRank'] = winner_data['Rank']
        game['OpponentGuild'] = opponent_data['Guild']
        game['OpponentRank'] = opponent_data['Rank']

        if game['WinnerGuild'] != game['OpponentGuild']:
            winner_data['Points'] = calc_points(winner_data['Points'], True)
            winner_data['Tournament Win/Loss'] = calc_win_loss(winner_data['Tournament Win/Loss'], True)
            opponent_data['Points'] = calc_points(opponent_data['Points'], False)
            opponent_data['Tournament Win/Loss'] = calc_win_loss(opponent_data['Tournament Win/Loss'], False)

            save_member_data(guild_members)

            game['WinnerPoints'] = winner_data['Points']
            game['WinnerWinLoss'] = winner_data['Tournament Win/Loss']
            game['OpponentPoints'] = opponent_data['Points']
            game['OpponentWinLoss'] = opponent_data['Tournament Win/Loss']

            valid_games.append(game)
        else:
            game['WinnerPoints'] = 'N/A'
            game['WinnerWinLoss'] = 'N/A'
            game['OpponentPoints'] = 'N/A'
            game['OpponentWinLoss'] = 'N/A'

            game['TableHeader'] = '[!SAME GUILD NOT SCORED!] ' + game['TableHeader']
            same_guild_games.append(game)


log.info('Valid Games: ' + pprint.pformat(valid_games))
log.info('Same Guild: ' + pprint.pformat(same_guild_games))

if valid_games or same_guild_games:
    log.info('Sending email...')
    send_email.process_email(
        {
            'games': valid_games,
            'same_guild': same_guild_games
        })
