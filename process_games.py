from bs4 import BeautifulSoup
import datetime
import re
import time
import urllib.request
import yaml

import guild_data
import send_email


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


print('Start : {}\n\n'.format(datetime.datatime.now()))
games_processed = load_games_processed()

guild_members = guild_data.get_guild_members()
for member, data in load_member_data().items():
    guild_members[member].update(data)

games = []

for member in guild_members:
    print('Processing: {}'.format(member))
    time.sleep(1)
    games_raw = urllib.request.urlopen('http://www.gokgs.com/gameArchives.jsp?user={}'.format(member))
    games_soup = BeautifulSoup(games_raw.read())

    for game in games_soup.table.find_all('tr')[1:]:
        tds = game.find_all('td')
        # This will also work where user played no games as game_viewable will be a 'Year' from the other table
        game_viewable = tds[0].text
        game_type = tds[-2].text

        if game_viewable == 'Yes' and game_type in ['Free', 'Ranked']:
            date = datetime.datetime.strptime(tds[4].text.strip(), '%m/%d/%y %I:%M %p')
            game_link = tds[0].a.get('href')
            game_setup = tds[3].text.strip()

            # only get games played today and where the board size is 19x19, that we haven't processed yet
            if date.date() == datetime.datetime.now().date() and game_setup.find('19×19') > -1 and game_link not in games_processed:
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

                winner = players[w_colour]['name']
                winnercolour = players[w_colour]['colour']
                opponent = players[o_colour]['name']
                opponentcolour = players[o_colour]['colour']

                winner_data = get_member_data(winner)
                opponent_data = get_member_data(opponent)

                winner_data['Points'] = calc_points(winner_data['Points'], True)
                winner_data['Tournament Win/Loss'] = calc_win_loss(winner_data['Tournament Win/Loss'], True)
                opponent_data['Points'] = calc_points(opponent_data['Points'], True)
                opponent_data['Tournament Win/Loss'] = calc_win_loss(opponent_data['Tournament Win/Loss'], True)

                game_data = {
                    'Link': game_link,
                    'Winner': winner,
                    'WinnerGuild': winner_data['Guild'],
                    'WinnerColour': winnercolour,
                    'WinnerRank': winner_data['Rank'],
                    'WinnerPoints': winner_data['Points'],
                    'WinnerWinLoss': winner_data['Tournament Win/Loss'],
                    'Opponent': opponent,
                    'OpponentGuild': opponent_data['Guild'],
                    'OpponentColour': opponentcolour,
                    'OpponentRank': opponent_data['Rank'],
                    'OpponentPoints': opponent_data['Points'],
                    'OpponentWinLoss': opponent_data['Tournament Win/Loss'],
                    'DatePlayed': date.date().strftime('%m/%d/%Y'),
                    'Result': result,
                }
                games.append(game_data)

                games_processed.append(game_link)
                save_member_data(guild_members)
                save_games_processed(games_processed)


valid_games = []
same_guild_games = []

for game in games:
    print('Retrieving: {}'.format(game['Link']))
    sgf_data = str(urllib.request.urlopen(game['Link']).read()).lower()
    if sgf_data.find('duelgo') > -1 or sgf_data.find('duel go') > -1:
        if game['WinnerGuild'] != game['OpponentGuild']:
            valid_games.append(game)
        else:
            same_guild_games.append(game)

print('Valid Games: {}'.format('\n'.join(valid_games)))
print('Same Guild: {}'.format('\n'.join(same_guild_games)))

if valid_games or same_guild_games:
    print('Sending email...')
    send_email.process_email(
        {
            'games': valid_games,
            'same_guild': same_guild_games
        })
