Introduction
------------

This is a collection of scripts to facilitate the automation of scoring games played on KGS for Leagues/Tournaments.

The main script queries KGS for games played by League members and downloads them to parse for the _keyword_ in the comments that identifies it as a league/tournament game.

Requirements
------------

The script requires the **YAML** and **BeautifulSoup4** Python libraries.

Scripts Breakdown
-----------------

| Script | Description |
| ------ | ----------- |
| query_kgs_archive.py | The main script and with a few modifications should work the way you want it to |
| send_email.py | Should be generic enough for reuse |
| games_template.html | Just an HTML table to format results (used by send_email.py) |
| config.yaml | Configuration for the scripts |
| games_seen.yaml | As the script can be run multiple times per day, this tracks the games already processed |
| guild_members.py | Specific to the League I wrote this for on KGS. |
| member_scores.yaml | Specific to the League I wrote this for on KGS (this will become a proper database with all member data) |

Future Plans
------------

I'm currently working on a web application that will allow the reqistering of Leagues, Guilds and members. The _keyword_ will be configurable and the entire scoring process will be handled automatically by the system. The query_kgs_archive.py script will form part of the backend.
