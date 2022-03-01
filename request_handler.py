from dotenv import dotenv_values  # pip install python-dotenv
import requests  # pip install requests
import json
from detector import DetectIfClubLeague
from datetime import datetime
from collections import defaultdict
import re
import httpx
import asyncio


token = dotenv_values(".env")["TOKEN"]
headers = {"Authorization": f"Bearer {token}"}


def get_club_stats(clubtag: str) -> str:
    clubtag = fix_tag_begin_hashtag(clubtag)
    assert is_tag_valid(clubtag), f"the provided tag ({clubtag[3:]}) is not valid, must only contain characters in \"pylqgrjcuv0289\""
    club_url = f"https://api.brawlstars.com/v1/clubs/{clubtag}"
    res = requests.get(club_url, headers=headers)
    return res.content.decode("utf-8")


def get_player_battlelog(playertag: str) -> str:
    playertag = fix_tag_begin_hashtag(playertag)
    assert is_tag_valid(playertag), f"the provided tag ({playertag[3:]}) is not valid, must only contain characters in \"pylqgrjcuv0289\""
    battlelog_url = f"https://api.brawlstars.com/v1/players/{playertag}/battlelog"
    res = requests.get(battlelog_url, headers=headers)
    return res.content.decode("utf-8")


def get_player_url(playertag: str) -> str:
    playertag = fix_tag_begin_hashtag(playertag)
    assert is_tag_valid(playertag), f"the provided tag ({playertag[3:]}) is not valid, must only contain characters in \"pylqgrjcuv0289\""
    return f"https://api.brawlstars.com/v1/players/{playertag}/battlelog"


def get_player_stats(playertag: str, current_log: list[str] = None) -> (int, int, list[int]):
    playertag = fix_tag_begin_hashtag(playertag)
    assert is_tag_valid(playertag), f"the provided tag ({playertag[3:]}) is not valid, must only contain characters in \"pylqgrjcuv0289\""
    log = get_player_battlelog(playertag)
    log = json.loads(log)["items"]
    detector = DetectIfClubLeague(log, current_log or [])
    return detector.detect_played()


def get_json_data_from_file(filename: str) -> dict:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return {}


async def stats_of_everyone_in_club(clubtag: str, outfile: str = None, records_file: str = None) -> None:
    assert outfile is None or outfile.endswith(".json"), "output file must be a json file"
    clubtag = fix_tag_begin_hashtag(clubtag)
    assert is_tag_valid(clubtag), f"the provided tag ({clubtag[3:]}) is not valid, must only contain characters in \"pylqgrjcuv0289\""

    print("Processing request...")

    stats = get_club_stats(clubtag)
    stats = json.loads(stats)

    print(f"Club found: {stats['name']}. Processing player data...")

    members = stats["members"]
    names_by_tags = {m["tag"]: m["name"] for m in members}

    # TODO: separate this logic into smaller functions

    if outfile is None:
        async with httpx.AsyncClient() as client:
            tasks = (client.get(get_player_url(member["tag"]), headers=headers) for member in members)
            reqs = await asyncio.gather(*tasks)

        total_trophies, total_tickets = 0, 0
        for res in reqs:
            content = res.content.decode("utf-8")
            _, tag, _ = re.split("%[2][3]|/[b]", str(res.url))
            name = names_by_tags["#" + tag]
            log = json.loads(content)["items"]
            detector = DetectIfClubLeague(log, [])
            tickets_used, trophies_gained, _ = detector.detect_played()
            total_trophies += trophies_gained
            total_tickets += tickets_used
            print(f"{name}: {tickets_used, trophies_gained}")
        print(f"total: {total_trophies: < 3} trophies, {total_tickets: <3} tickets")
        return

    player_data = get_json_data_from_file(outfile)
    player_data = defaultdict(lambda: {"name": "", "tickets": 0, "trophies": 0, "games": []}, player_data)
    # convert to a default dict for ease of use

    async with httpx.AsyncClient() as client:
        tasks = (client.get(get_player_url(member["tag"]), headers=headers) for member in members)
        reqs = await asyncio.gather(*tasks)

    total_trophies, total_tickets = 0, 0
    for res in reqs:
        content = res.content.decode("utf-8")
        _, tag, _ = re.split("%[2][3]|/[b]", str(res.url))
        tag = "#" + tag
        data = player_data[tag]
        name = names_by_tags[tag]
        battle_log = json.loads(content)["items"]
        detector = DetectIfClubLeague(battle_log, data["games"])
        tickets_used, trophies_gained = detector.detect_played()
        print(f"{name:<16} has {tickets_used} more tickets and {trophies_gained} more trophies than last time")
        data["name"] = name
        data["tickets"] += tickets_used
        data["trophies"] += trophies_gained
        data["games"] = [i["battleTime"] for i in battle_log]
        player_data[tag] = data

        total_trophies += data["trophies"]
        total_tickets += data["tickets"]
    print(f"total: {total_trophies: < 3} trophies, {total_tickets: <3} tickets")

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(player_data, f, indent=4)

    if records_file is None:
        return

    assert records_file.endswith(".json"), "records file must be a json file"

    historic_data = get_json_data_from_file(records_file)
    historic_data[days_since_clubwar() // 7] = player_data

    with open(records_file, "w", encoding="utf-8") as f:
        json.dump(historic_data, f, indent=4)


def clear_data(filename: str) -> None:
    assert filename.endswith(".json"), "file must be a json file"
    data = get_json_data_from_file(filename)
    assert data != {}, "cannot clear data from empty file"

    for tag, player_data in data.items():
        new_data = player_data
        new_data["tickets"]  = 0
        new_data["trophies"] = 0
        data[tag] = new_data

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def fix_tag_begin_hashtag(tag: str) -> str:
    if tag[:3] == "%23":
        return tag
    if tag[0] == "#":
        return "%23" + tag[1:]
    return "%23" + tag


def is_tag_valid(tag: str) -> bool:
    available_chars = "pylqgrjcuv0289"
    begin, tag = tag[:3], tag[3:]
    return begin == "%23" and all([i.lower() in available_chars for i in tag])


def calculate_days_since(battletime: str, output_type: str = "seconds") -> int:
    assert output_type in ["weeks", "days", "hours", "minutes", "seconds"]
    now = datetime.utcnow()
    battle_date_str, battle_time_str, _ = re.split("[T.]", battletime)
    indices = [0, 4, 6]
    year, month, day = [int(battle_date_str[i:j]) for i, j in zip(indices, indices[1:]+[None])]
    hour, minute, second = [battle_time_str[i:i+2] for i in range(0, 6, 2)]
    battle_date = datetime(year, month, day, hour, minute, second)
    seconds = int((now - battle_date).total_seconds())
    match output_type:
        case "weeks":
            return seconds * 60 * 60 * 24 * 7
        case "days":
            return seconds * 60 * 60 * 24
        case "hours":
            return seconds * 60 * 60
        case "minutes":
            return seconds * 60
        case "seconds":
            return seconds


def days_since_clubwar(time: datetime = datetime.utcnow()) -> int:
    known_CW_day = datetime(2022, 2, 16, 14, 0, 0)  # UTC time
    seconds_since = int((time - known_CW_day).total_seconds())
    days_since = seconds_since // (60 * 60 * 24)
    return days_since


def is_it_a_club_war_day(time: datetime = datetime.utcnow()) -> bool:
    return (days_since_clubwar(time) % 7) in [0, 2, 4]


def is_club_war_over(time: datetime = datetime.utcnow()):
    return (days_since_clubwar(time) % 7) in [5, 6]
