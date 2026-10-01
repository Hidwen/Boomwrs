from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import os
import uuid
import game
import party_manager

app = Flask(__name__)
app.secret_key = os.urandom(24)

GAMES = {}
game.load_words()

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        code = request.form.get("code", "").upper().strip()
        if len(username) >= 3 and len(username) <= 12 and username.isalnum():
            session["username"] = username
            if code:
                party = party_manager.get_party(code)
                if party:
                    success, msg = party.join(username)
                    if success:
                        session["party_code"] = party.code
                        return redirect(url_for("party_lobby"))
            return redirect(url_for("travel"))
        else:
            return render_template("home.html", error="Name must be 3-12 letters and numbers only.")
    
    return render_template("home.html", username=session.get("username"))

@app.route("/travel")
def travel():
    if "username" not in session:
        return redirect(url_for("home"))
    return render_template("travel.html", username=session.get("username"))

@app.route("/play")
def play():
    if "username" not in session:
        return redirect(url_for("home"))
        
    game_id = str(uuid.uuid4())
    session["game_id"] = game_id
    
    answer = game.pick_word()
    GAMES[game_id] = {
        "answer": answer,
        "guesses": [],
        "draft": "",
        "status": "playing",
        "message": "",
        "new_row": False
    }
    
    return redirect(url_for("game_board"))

def generate_confetti():
    import random
    pieces = []
    colors = ["#2fa866", "#f4a62a", "#00b4d8", "#ffffff"]
    for _ in range(80):
        piece = {
            "left": f"{random.randint(0, 100)}vw",
            "delay": f"{random.uniform(0, 2):.2f}s",
            "duration": f"{random.uniform(2, 4):.2f}s",
            "size": f"{random.randint(5, 15)}px",
            "color": random.choice(colors),
            "rotation": f"{random.randint(0, 360)}deg"
        }
        pieces.append(piece)
    return pieces

@app.route("/game")
def game_board():
    if "username" not in session:
        return redirect(url_for("home"))
    if "game_id" not in session or session["game_id"] not in GAMES:
        return redirect(url_for("travel"))
        
    current_game = GAMES[session["game_id"]]
    
    scored_guesses = []
    for g in current_game["guesses"]:
        scores = game.score_guess(g, current_game["answer"])
        scored_guesses.append((g, scores))
        
    kb_colors = game.keyboard_colors(current_game["guesses"], current_game["answer"])
    
    confetti = []
    if current_game["status"] in ["won", "lost"]:
        confetti = generate_confetti()
    
    return render_template("game.html", 
                           game=current_game, 
                           username=session.get("username"),
                           scored_guesses=scored_guesses,
                           kb_colors=kb_colors,
                           word_length=len(current_game["answer"]),
                           confetti=confetti)

@app.route("/guess", methods=["POST"])
def guess():
    if "game_id" not in session or session["game_id"] not in GAMES:
        return redirect(url_for("travel"))
        
    current_game = GAMES[session["game_id"]]
    
    if current_game["status"] != "playing":
        return redirect(url_for("game_board"))
        
    current_game["message"] = ""
    current_game["new_row"] = False
    
    typed_word = request.form.get("word", "").lower()
    word_length = len(current_game["answer"])
    
    if len(typed_word) != word_length:
        current_game["message"] = "Not enough letters"
    elif not game.is_real_word(typed_word):
        current_game["message"] = "No such word is present"
    else:
        current_game["guesses"].append(typed_word)
        current_game["new_row"] = True
        
        if typed_word == current_game["answer"]:
            current_game["status"] = "won"
            current_game["message"] = "You win!"
        elif len(current_game["guesses"]) >= 6:
            current_game["status"] = "lost"
            current_game["message"] = "You lose!"

    return redirect(url_for("game_board"))

@app.route("/forfeit")
def forfeit():
    if "game_id" in session and session["game_id"] in GAMES:
        del GAMES[session["game_id"]]
        del session["game_id"]
    return redirect(url_for("travel"))

# ==================== PARTY ROUTES ====================

@app.route("/party/create", methods=["POST"])
def party_create():
    if "username" not in session:
        return redirect(url_for("home"))
    username = session["username"]
    party = party_manager.create_party(username)
    session["party_code"] = party.code
    return redirect(url_for("party_lobby"))

@app.route("/party/join", methods=["GET", "POST"])
def party_join():
    code = request.values.get("code", "").upper().strip()
    
    if request.method == "GET":
        if "username" in session:
            party = party_manager.get_party(code)
            if party:
                success, msg = party.join(session["username"])
                if success:
                    session["party_code"] = party.code
                    return redirect(url_for("party_lobby"))
                else:
                    return render_template("travel.html", username=session["username"], error=msg)
            else:
                return render_template("travel.html", username=session["username"], error="Party not found.")
        else:
            # Prompt username entry prefilled with code
            return render_template("home.html", join_code=code)

    if "username" not in session:
        return redirect(url_for("home"))
        
    username = session["username"]
    party = party_manager.get_party(code)
    if not party:
        return render_template("travel.html", username=username, error="Invalid Party Code!")
        
    success, msg = party.join(username)
    if not success:
        return render_template("travel.html", username=username, error=msg)

    session["party_code"] = party.code
    return redirect(url_for("party_lobby"))

@app.route("/party/lobby")
def party_lobby():
    if "username" not in session:
        return redirect(url_for("home"))
    if "party_code" not in session:
        return redirect(url_for("travel"))
    return render_template("party.html", username=session["username"])

@app.route("/party/settings", methods=["POST"])
def party_settings():
    if "username" not in session or "party_code" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    party = party_manager.get_party(session["party_code"])
    if not party:
        return jsonify({"error": "Party not found"}), 404
        
    rounds = request.form.get("total_rounds", 5)
    timer_limit = request.form.get("round_timer_limit", 60)
    muted = request.form.get("chat_muted") == '1'
    party.update_settings(session["username"], rounds, timer_limit, muted)
    return jsonify({"success": True})

@app.route("/party/chat", methods=["POST"])
def party_chat():
    if "username" not in session or "party_code" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    party = party_manager.get_party(session["party_code"])
    if not party:
        return jsonify({"error": "Party not found"}), 404
        
    text = request.form.get("text", "")
    success, msg = party.add_message(session["username"], text)
    return jsonify({"success": success, "message": msg})

@app.route("/party/start", methods=["POST"])
def party_start():
    if "username" not in session or "party_code" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    party = party_manager.get_party(session["party_code"])
    if not party:
        return jsonify({"error": "Party not found"}), 404
        
    success, msg = party.start_game(session["username"])
    return jsonify({"success": success, "message": msg})

@app.route("/party/kick", methods=["POST"])
def party_kick():
    if "username" not in session or "party_code" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    party = party_manager.get_party(session["party_code"])
    if not party:
        return jsonify({"error": "Party not found"}), 404
        
    target = request.form.get("target", "")
    success, msg = party.kick(session["username"], target)
    return jsonify({"success": success, "message": msg})

@app.route("/party/leave", methods=["POST"])
def party_leave():
    if "party_code" in session:
        party = party_manager.get_party(session["party_code"])
        if party and "username" in session:
            party.leave(session["username"])
        del session["party_code"]
    return jsonify({"success": True})

@app.route("/party/forfeit", methods=["POST"])
def party_forfeit():
    if "party_code" in session and "username" in session:
        party = party_manager.get_party(session["party_code"])
        if party:
            party.forfeit_player(session["username"])
        del session["party_code"]
    return jsonify({"success": True})

@app.route("/party/disband", methods=["POST"])
def party_disband():
    if "party_code" in session and "username" in session:
        party = party_manager.get_party(session["party_code"])
        if party and party.host == session["username"]:
            if party.code in party_manager.PARTIES:
                del party_manager.PARTIES[party.code]
        del session["party_code"]
    return jsonify({"success": True})

@app.route("/api/party/status")
def party_status():
    if "username" not in session or "party_code" not in session:
        return jsonify({"error": "Not in party"}), 401
    party = party_manager.get_party(session["party_code"])
    if not party:
        return jsonify({"is_member": False})
    return jsonify(party.get_status(session["username"]))

@app.route("/api/party/guess", methods=["POST"])
def party_guess():
    if "username" not in session or "party_code" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    party = party_manager.get_party(session["party_code"])
    if not party:
        return jsonify({"error": "Party not found"}), 404
        
    word = request.form.get("word", "")
    success, msg = party.submit_guess(session["username"], word)
    return jsonify({"success": success, "message": msg})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
