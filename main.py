from request_handler import *
from time import sleep

wrote_to_records = False
cleared_data = False


def main():
    global wrote_to_records, cleared_data

    test_clubtag = "VJ2Y0GUC"
    test_playertag = "#9qjugrc9"

    week_data_filename = "data.json"
    records_filename = "records.json"

    if is_it_a_club_war_day():
        asyncio.run(stats_of_everyone_in_club(test_clubtag, week_data_filename, records_filename))
        print("data found! re-fetching data in 30 minutes", datetime.now())
        wrote_to_records = False
        cleared_data = False
    # continuously update the stats during days when there is a club war going on
    elif not wrote_to_records:
        asyncio.run(stats_of_everyone_in_club(test_clubtag, week_data_filename, records_filename))
        if is_club_war_over():
            print("data found! Club league is over! booting up again in 2 days", datetime.now())
        else:
            print(f"data found! Day {1 + (days_since_clubwar() % 7) // 2} of club war is over, re-fetching in a day", datetime.now())
        wrote_to_records = True
    # update the stats one last time after club war day has finished
    if is_club_war_over() and not cleared_data:
        clear_data(week_data_filename)
    # once the club war has finished, clear the trophies/tickets of everyone


if __name__ == '__main__':
    while True:
        main()
        sleep(60 * 30)  # 30 minutes

