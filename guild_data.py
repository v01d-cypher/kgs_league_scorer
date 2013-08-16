from bs4 import BeautifulSoup
import logging
import time
import urllib.request

logging.basicConfig(
    filename='/var/log/duelgo.log',
    level=logging.INFO,
    datefmt='%Y%m%d %H%M',
    format='%(asctime)s : %(levelname)s %(name)s - %(message)s')

log = logging.getLogger('[Guild-Data]')


def _get_guild_data():
    guild_names_raw = urllib.request.urlopen('http://duelgo.webs.com/guilds')
    guild_names_soup = BeautifulSoup(guild_names_raw.read())

    page_links = (
        'Home',
        'Guilds',
        'Forums',
        'Rules')

    guild_data = {}

    for link in guild_names_soup.find_all('a'):
        name = link.text
        if name not in page_links:
            guild_data[name] = link.get('href')

    return guild_data


def get_guild_members():
    guild_data = _get_guild_data()

    member_data_items = (
        'Rank',
        'Tournament Win/Loss',
        'Guild Rank',
        'Points'
    )

    guild_members = {}

    for name, link in guild_data.items():
        log.info('Guild: {}'.format(name))
        #sleep else web calls appear to be too fast for site
        time.sleep(2)

        members_raw = urllib.request.urlopen(link)
        members_soup = BeautifulSoup(members_raw.read())

        # first tr is weird shit, second tr is headings
        for member in members_soup.table.find_all('tr')[2:]:
            tds = member.find_all('td')

            username = tds[0].text.strip()
            if username:
                username_key = username.lower()
                guild_members[username_key] = {
                    'Guild': name
                }
                log.info('\t{}'.format(username))

                guild_members[username_key]['Name'] = username

                for index, td in enumerate(tds[1:5]):
                    guild_members[username_key][member_data_items[index]] = td.text.strip()

    return guild_members


if __name__ == '__main__':
    guild_members = get_guild_members()

    import pprint
    pprint.pprint(guild_members)
