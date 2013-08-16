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


logging.basicConfig(
    filename='/var/log/duelgo.log',
    level=logging.INFO,
    datefmt='%Y%m%d %H%M',
    format='%(asctime)s : %(levelname)s %(name)s - %(message)s')

log = logging.getLogger('[DuelGo]')


def load_games_seen():
    return yaml.load(open('games_seen.yaml', 'rb'))


def save_games_seen(games_seen):
    yaml.dump(games_seen, open('games_seen.yaml', 'w', encoding='UTF-8'), default_flow_style=False)


def load_member_scores():
    return yaml.load(open('member_scores.yaml', 'rb'))


def save_member_scores(guild_members):
    yaml_data = {}
    for member, data in guild_members.items():
        yaml_data[member] = {
            'Points': data['Points'],
            'Tournament Win/Loss': data['Tournament Win/Loss']
        }
    yaml.dump(yaml_data, open('member_scores.yaml', 'w', encoding='UTF-8'), default_flow_style=False)


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


def query_games(guild_members):
    games = []
    games_seen = load_games_seen()

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

            white_player = re.sub(r'(.*)\[.*', r'\1', tds[1].text).strip().lower()
            black_player = re.sub(r'(.*)\[.*', r'\1', tds[2].text).strip().lower()

            # Only bother doing anything with the game data if both the players are members of known guilds
            if white_player in guild_members and black_player in guild_members:
                players = {
                    'W': {
                        'key': white_player,
                        'name': guild_members[white_player]['Name'],
                        'colour': 'White'},
                    'B': {
                        'key': black_player,
                        'name': guild_members[black_player]['Name'],
                        'colour': 'Black'}}

                game_viewable = tds[0].text
                game_setup = tds[3].text.strip()
                game_type = tds[-2].text

                # This will also work where user played no games as game_viewable will be a 'Year' from the other table
                if game_viewable == 'Yes' and game_type in ['Free', 'Ranked'] and game_setup.find('19×19') > -1:
                    date = datetime.datetime.strptime(tds[4].text.strip(), '%m/%d/%y %I:%M %p')
                    game_link = tds[0].a.get('href')

                    # Get all games for previous day, that we haven't processed yet
                    if date.date() == datetime.datetime.now().date() - datetime.timedelta(1) and game_link not in games_seen:
                        log.info('\t{}'.format(game_link))

                        winner_colour = 'B'
                        opponent_colour = 'W'

                        result = tds[6].text.strip()

                        if result[0] != winner_colour:
                            winner_colour, opponent_colour = opponent_colour, winner_colour

                        game_data = {
                            'Link': game_link,
                            'winner_key': players[winner_colour]['key'],
                            'Winner': players[winner_colour]['name'],
                            'WinnerColour': players[winner_colour]['colour'],
                            'opponent_key': players[opponent_colour]['key'],
                            'Opponent': players[opponent_colour]['name'],
                            'OpponentColour': players[opponent_colour]['colour'],
                            'DatePlayed': date.date().strftime('%m/%d/%Y'),
                            'Result': result,
                        }

                        games.append(game_data)
                        games_seen.append(game_link)

    log.info('Games found: ' + pprint.pformat(games))
    save_games_seen(games_seen)

    return games


def process_games(games):
    processed_games = {
        'valid': [],
        'same_guild': []
    }

    for index, game in enumerate(games):
        log.info('Retrieve Game #{}: {}'.format(index + 1, game['Link']))
        # www.gokgs.com has a time limit between requests. Don't know how much time yet. 5 seconds seems to work for now.
        time.sleep(5)

        sgf_data = str(urllib.request.urlopen(game['Link']).read()).lower()

        if sgf_data.find('duelgo') > -1 or sgf_data.find('duel go') > -1:
            game['TableHeader'] = 'Game - {} vs. {}'.format(game['Winner'], game['Opponent'])

            winner_data = get_member_data(game['winner_key'])
            opponent_data = get_member_data(game['opponent_key'])

            game['WinnerGuild'] = winner_data['Guild']
            game['WinnerRank'] = winner_data['Rank']
            game['OpponentGuild'] = opponent_data['Guild']
            game['OpponentRank'] = opponent_data['Rank']

            if game['WinnerGuild'] != game['OpponentGuild'] and game['Result'] != 'Unfinished':
                winner_data['Points'] = calc_points(winner_data['Points'], True)
                winner_data['Tournament Win/Loss'] = calc_win_loss(winner_data['Tournament Win/Loss'], True)
                opponent_data['Points'] = calc_points(opponent_data['Points'], False)
                opponent_data['Tournament Win/Loss'] = calc_win_loss(opponent_data['Tournament Win/Loss'], False)

                game['WinnerPoints'] = winner_data['Points']
                game['WinnerWinLoss'] = winner_data['Tournament Win/Loss']
                game['OpponentPoints'] = opponent_data['Points']
                game['OpponentWinLoss'] = opponent_data['Tournament Win/Loss']

                processed_games['valid'].append(game)

            else:
                game['WinnerPoints'] = 'N/A'
                game['WinnerWinLoss'] = 'N/A'
                game['OpponentPoints'] = 'N/A'
                game['OpponentWinLoss'] = 'N/A'

                if game['Result'] == 'Unfinished':
                    game['TableHeader'] = '[Unfinished] ' + game['TableHeader']
                    processed_games['valid'].append(game)
                else:
                    game['TableHeader'] = '[Same Guild NOT Scored] ' + game['TableHeader']
                    processed_games['same_guild'].append(game)

    save_member_scores(guild_members)

    log.info('Games processed: ' + pprint.pformat(processed_games))
    return processed_games


log.info('Start processing')

# Load guild members and update scores to what we last calculated
guild_members = guild_data.get_guild_members()
for member, scores in load_member_scores().items():
    if member in guild_members:
        guild_members[member].update(scores)


games = query_games(guild_members)
processed_games = process_games(games)

if processed_games['valid'] or processed_games['same_guild']:
    log.info('Sending email...')
    send_email.process_email(processed_games)
