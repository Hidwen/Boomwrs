import random
import string
import time
import game

PARTIES = {}

def generate_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=6))
        if code not in PARTIES:
            return code

class Party:
    def __init__(self, code, host):
        self.code = code
        self.host = host
        self.players = [host]
        self.kicked = set()
        self.status = 'lobby'  # 'lobby', 'playing', 'break', 'podium'
        self.total_rounds = 5  # min 4, max 10
        self.round_timer_limit = 60  # min 30s, max 180s, default 60s
        self.current_round = 0
        self.chat_muted = False
        self.messages = []  # list of {id, sender, text, timestamp}
        self.msg_counter = 0
        self.events = []  # list of {id, text, timestamp}
        self.event_counter = 0
        
        # Round data
        self.round_word = ""
        self.round_start_time = 0
        self.round_finishers = []  # list of usernames in order of correct guess
        self.player_round_states = {}  # username -> {guesses: [], status: 'playing'/'won'/'lost', duration: float, points: int}
        self.scores = {host: 0}  # username -> total_points
        self.break_start_time = 0
        self.podium_start_time = 0
        self.last_activity = time.time()
        
        # Initial join event
        self.add_event(f"{host} created the party.")

    def add_message(self, sender, text):
        if self.chat_muted and sender != self.host:
            return False, "Chat is muted by host."
        text = text.strip()[:100]
        if not text:
            return False, "Empty message."
        self.msg_counter += 1
        self.messages.append({
            "id": self.msg_counter,
            "sender": sender,
            "text": text,
            "timestamp": time.strftime("%H:%M")
        })
        if len(self.messages) > 50:
            self.messages.pop(0)
        return True, "Message sent."

    def add_event(self, text):
        self.event_counter += 1
        self.events.append({
            "id": self.event_counter,
            "text": text,
            "timestamp": time.time()
        })
        if len(self.events) > 30:
            self.events.pop(0)

    def join(self, username):
        if username in self.kicked:
            return False, "You have been kicked out of this party."
        if self.status != 'lobby':
            return False, "Party game is currently in progress."
        if username not in self.players:
            self.players.append(username)
            self.scores[username] = 0
            self.add_event(f"{username} joined the game.")
        return True, "Joined party."

    def leave(self, username):
        if username in self.players:
            self.players.remove(username)
            self.add_event(f"{username} left the party.")
            if username == self.host:
                if self.players:
                    self.host = self.players[0]  # Transfer host
                    self.add_event(f"{self.host} is now the host.")
                else:
                    if self.code in PARTIES:
                        del PARTIES[self.code]
                    return True, "Party closed."
        return True, "Left party."

    def forfeit_player(self, username):
        if username in self.players:
            self.add_event(f"{username} forfeits.")
            if username in self.player_round_states:
                self.player_round_states[username]["status"] = "lost"
            return self.leave(username)
        return True, "Forfeited."

    def kick(self, host_username, target_username):
        if host_username != self.host:
            return False, "Only party host can kick players."
        if target_username in self.players:
            self.players.remove(target_username)
            self.kicked.add(target_username)
            self.add_event(f"{target_username} was kicked from the party.")
            return True, f"{target_username} was kicked."
        return False, "Player not found."

    def update_settings(self, host_username, total_rounds, round_timer_limit, chat_muted):
        if host_username != self.host:
            return False, "Only party host can change settings."
        try:
            rounds = int(total_rounds)
            if 4 <= rounds <= 10:
                self.total_rounds = rounds
        except ValueError:
            pass

        try:
            t_limit = int(round_timer_limit)
            if 30 <= t_limit <= 180:
                self.round_timer_limit = t_limit
        except ValueError:
            pass

        self.chat_muted = bool(chat_muted)
        self.add_event("Host updated party settings.")
        return True, "Settings updated."

    def start_game(self, host_username):
        if host_username != self.host:
            return False, "Only party host can start the game."
        if len(self.players) < 1:
            return False, "Need at least 1 player."
        
        self.current_round = 1
        self.scores = {p: 0 for p in self.players}
        self.start_new_round()
        self.add_event("Match started!")
        return True, "Game started."

    def start_new_round(self):
        self.status = 'playing'
        self.round_word = game.pick_word()
        self.round_start_time = time.time()
        self.round_finishers = []
        self.player_round_states = {}
        for p in self.players:
            self.player_round_states[p] = {
                "guesses": [],
                "status": "playing",  # 'playing', 'won', 'lost'
                "duration": float(self.round_timer_limit),
                "points": 0
            }

    def process_time_tick(self):
        now = time.time()
        if self.status == 'playing':
            elapsed = now - self.round_start_time
            all_done = True
            for p in self.players:
                pstate = self.player_round_states.get(p)
                if not pstate:
                    continue
                if pstate["status"] == "playing":
                    if elapsed >= float(self.round_timer_limit):
                        pstate["status"] = "lost"
                        pstate["duration"] = float(self.round_timer_limit)
                    else:
                        all_done = False
            
            if all_done or elapsed >= float(self.round_timer_limit):
                self.finish_round()

        elif self.status == 'break':
            elapsed = now - self.break_start_time
            if elapsed >= 5.0:  # 5 seconds leaderboard break
                if self.current_round < self.total_rounds:
                    self.current_round += 1
                    self.start_new_round()
                else:
                    self.status = 'podium'
                    self.podium_start_time = now

        elif self.status == 'podium':
            elapsed = now - self.podium_start_time
            if elapsed >= 10.0:  # 10 seconds podium display
                self.status = 'lobby'

    def finish_round(self):
        self.status = 'break'
        self.break_start_time = time.time()
        
        points_table = [5, 3, 2]
        for idx, finisher in enumerate(self.round_finishers):
            pts = points_table[idx] if idx < len(points_table) else 1
            if finisher in self.player_round_states:
                self.player_round_states[finisher]["points"] = pts
                self.scores[finisher] = self.scores.get(finisher, 0) + pts

    def submit_guess(self, username, typed_word):
        if self.status != 'playing':
            return False, "Not in playing state."
        pstate = self.player_round_states.get(username)
        if not pstate or pstate["status"] != "playing":
            return False, "Cannot guess right now."

        now = time.time()
        elapsed = now - self.round_start_time
        if elapsed >= float(self.round_timer_limit):
            pstate["status"] = "lost"
            pstate["duration"] = float(self.round_timer_limit)
            return False, "Time is up!"

        word_len = len(self.round_word)
        typed_word = typed_word.lower().strip()

        if len(typed_word) != word_len:
            return False, "Not enough letters"
        if not game.is_real_word(typed_word):
            return False, "No such word is present"

        pstate["guesses"].append(typed_word)
        
        if typed_word == self.round_word:
            pstate["status"] = "won"
            pstate["duration"] = round(elapsed, 2)
            self.round_finishers.append(username)
            self.add_event(f"{username} guessed it!")
            self.process_time_tick()
            return True, "Correct guess!"
        elif len(pstate["guesses"]) >= 6:
            pstate["status"] = "lost"
            pstate["duration"] = float(self.round_timer_limit)
            self.process_time_tick()
            return True, "Out of guesses"

        return True, "Valid guess"

    def get_rankings(self):
        sorted_players = sorted(self.players, key=lambda p: (-self.scores.get(p, 0), p))
        rankings = []
        for i, p in enumerate(sorted_players):
            if i > 0 and self.scores.get(p, 0) == self.scores.get(sorted_players[i-1], 0):
                rank = rankings[-1]["rank"]
            else:
                rank = i + 1
            rankings.append({
                "rank": rank,
                "username": p,
                "score": self.scores.get(p, 0)
            })
        return rankings

    def get_status(self, username):
        self.process_time_tick()
        now = time.time()

        is_kicked = username in self.kicked
        is_member = username in self.players

        pstate = self.player_round_states.get(username, {})
        guesses = pstate.get("guesses", [])
        
        scored_guesses = []
        if self.round_word:
            for g in guesses:
                scored_guesses.append((g, game.score_guess(g, self.round_word)))
        kb_colors = game.keyboard_colors(guesses, self.round_word) if self.round_word else {}

        time_left = 0
        if self.status == 'playing':
            time_left = max(0, int(self.round_timer_limit - (now - self.round_start_time)))
        elif self.status == 'break':
            time_left = max(0, int(5 - (now - self.break_start_time)))
        elif self.status == 'podium':
            time_left = max(0, int(10 - (now - self.podium_start_time)))

        return {
            "code": self.code,
            "host": self.host,
            "is_host": (username == self.host),
            "is_kicked": is_kicked,
            "is_member": is_member,
            "players": self.players,
            "status": self.status,
            "total_rounds": self.total_rounds,
            "round_timer_limit": self.round_timer_limit,
            "current_round": self.current_round,
            "chat_muted": self.chat_muted,
            "messages": self.messages,
            "events": self.events,
            "time_left": time_left,
            "round_word": self.round_word if self.status == 'break' else ("***" if pstate.get("status") != "won" else self.round_word),
            "word_length": len(self.round_word) if self.round_word else 5,
            "player_status": pstate.get("status", "playing"),
            "guesses": guesses,
            "scored_guesses": scored_guesses,
            "kb_colors": kb_colors,
            "rankings": self.get_rankings(),
            "round_finishers": self.round_finishers
        }

def create_party(host):
    code = generate_code()
    party = Party(code, host)
    PARTIES[code] = party
    return party

def get_party(code):
    if not code:
        return None
    return PARTIES.get(code.upper().strip())
