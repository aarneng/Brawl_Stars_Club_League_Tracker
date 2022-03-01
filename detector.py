class DetectIfClubLeague:
    def __init__(self, battlelog, data):
        self.trophy_changes = {
            "teamRanked": {
                "victory": [7, 9],
                "tie": [],
                "defeat": [3, 5]
            },
            "ranked": {
                "victory": [3, 4],
                "tie": [2, 3],
                "defeat": [1, 2]
            }
        }
        self.battlelog = battlelog
        self.data = data

    def detect_played(self):
        tickets_used = 0
        trophies_gained = 0
        for battle in self.battlelog:
            # use battletime as pseudo-unique ID
            if battle["battleTime"] in self.data:
                continue
            is_cl_battle, battle_type, trophy_change = self.is_a_club_league_battle(battle)
            if not is_cl_battle:
                continue
            if battle_type == "teamRanked":
                tickets_used += 2
            else:
                tickets_used += 1
            trophies_gained += trophy_change
        return tickets_used, trophies_gained

    def is_a_club_league_battle(self, battle):
        # is the battle's trophy change consistent with a club league game's trophy change?
        battle = battle["battle"]
        tr_delta = battle.get("trophyChange", None)
        try:
            valid_deltas = self.trophy_changes[battle["type"]][battle["result"]]
        except KeyError as e:
            # print("error", e, battle)
            valid_deltas = []
        return tr_delta in valid_deltas, battle.get("type", None), tr_delta
