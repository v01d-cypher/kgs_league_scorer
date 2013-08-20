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


def load_games_seen():
    return yaml.load(open('games_seen.yaml', 'rb'))


def save_games_seen(games_seen, datenow):
    # We remove games older than 2 days.
    for key in list(games_seen.keys()):
        if key < datenow.date() - datetime.timedelta(1):
            del games_seen[key]

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


def get_member_data(member, guild_members):
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


def get_games_from_kgs(guild_members):
    games = []
    games_seen = load_games_seen()
    datenow = datetime.datetime.now()

    for index, member in enumerate(guild_members):
        log.info('Query User #{}: {}'.format(index + 1, member))
        # www.gokgs.com has a time limit between requests. Don't know how much time yet, but 5 seconds seems to work.
        time.sleep(5)

        # We pass in our timezone as a cookie so that we're always processing against our time
        request = urllib.request.Request(
            'http://www.gokgs.com/gameArchives.jsp?user={}'.format(member),
            headers={'Cookie': '{}'.format(config['timezone'])})

        games_raw = urllib.request.urlopen(request)
        games_soup = BeautifulSoup(games_raw.read())

        for game in games_soup.table.find_all('tr')[1:]:
            tds = game.find_all('td')

            white_player = re.sub(r'(.*)\[.*', r'\1', tds[1].text).strip().lower()
            black_player = re.sub(r'(.*)\[.*', r'\1', tds[2].text).strip().lower()

            # Only bother doing anything with the game data if both players are members of known guilds
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
                    game_link = tds[0].a.get('href')
                    date_played = datetime.datetime.strptime(tds[4].text.strip(), '%m/%d/%y %I:%M %p')

                    # Get all games that we haven't processed yet
                    if (game_link not in games_seen.setdefault(datenow.date(), []) and
                        (date_played.date() == datenow.date() or
                         date_played.date() == datenow.date() - datetime.timedelta(1))):

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
                            'DatePlayed': date_played.date().strftime(config['dateformat']),
                            'Result': result,
                        }

                        games.append(game_data)
                        games_seen[datenow].append(game_link)

    save_games_seen(games_seen, datenow)

    log.info('Games found: ' + pprint.pformat(games))

    return games


def process_games(games, guild_members):
    processed_games = {
        'valid': [],
        'same_guild': []
    }

    for index, game in enumerate(games):
        log.info('Retrieve Game #{}: {}'.format(index + 1, game['Link']))
        # www.gokgs.com has a time limit between requests. Don't know how much time yet, but 5 seconds seems to work.
        time.sleep(5)

        sgf_data = str(urllib.request.urlopen(game['Link']).read()).lower()

        if re.search(config['game_key'].lower(), sgf_data.lower()):
            game['TableHeader'] = 'Game - {} vs. {}'.format(game['Winner'], game['Opponent'])

            winner_data = get_member_data(game['winner_key'], guild_members)
            opponent_data = get_member_data(game['opponent_key'], guild_members)

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


def get_guild_members():
    # Load guild members and update scores from yaml db.
    # We assume our data is the most up to date.
    #
    # guild members should be a dictionary with the following format:
    #
    # guild_members {
    #   member1: {  # make sure this is the member name lowercased
    #       'Name': 'MemBer1',
    #       'Rank': '1d',
    #       'Guild': 'Some Guild',
    #       'Points': '0',
    #       'Tournament Win/Loss': '0/0'},
    #   othermember: {  # make sure this is the member name lowercased
    #       'Name': 'OtherMember',
    #       'Rank': '1k',
    #       'Guild': 'Another Guild',
    #       'Points': '1',
    #       'Tournament Win/Loss': '1/0'}}

    guild_members = guild_data.get_guild_members()
    for member, scores in load_member_scores().items():
        if member in guild_members:
            guild_members[member].update(scores)
    return guild_members


def main():
    log.info('Start processing')

    guild_members = get_guild_members()
    games = get_games_from_kgs(guild_members)
    processed_games = process_games(games, guild_members)

    if processed_games['valid'] or processed_games['same_guild']:
        log.info('Sending email...')
        send_email.process_email(processed_games)


if __name__ == '__main__':
    config = yaml.load(open('config.yaml', 'rb'))

    logging.basicConfig(
        filename=config['logfile'],
        level=logging.INFO,
        datefmt='%Y%m%d %H%M',
        format='%(asctime)s : %(levelname)s %(name)s - %(message)s')
    log = logging.getLogger('[DuelGo]')

    main()
