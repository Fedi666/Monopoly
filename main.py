import json
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from uuid import uuid4
import logging
app = Flask(__name__)
app.secret_key = "abcdefghijklmnopqrstuvwxyz"

# Constantes du jeu
MAX_JOUEURS = 8
NUM_CASES = 40
JAIL_POSITION = 10
JAIL_FINE = 50
START_BONUS = 200
NUM_CARTE_CAISSE = 14
NUM_CARTE_CHANCE = 7
GAIN = 2000
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "adminadmin"


# Set up logging to track AI decisions
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
def get_db_connection():
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="monopoly"
    )
    return conn

# AI Class for 1 vs 1 mode
class MonopolyLearningAI:
    AI_IDENTIFIER = "MonopolyAI"  # Fixed identifier for single AI model

    def __init__(self, difficulty="medium"):
        self.difficulty = difficulty
        self.cash_buffer = 200 if difficulty == "hard" else 300 if difficulty == "medium" else 400
        self.learning_rate = 0.1
        self.game_round = 0
        self.rules = {
            "buy_property": {
                "weight": 0.9 if difficulty == "hard" else 0.7 if difficulty == "medium" else 0.5,
                "condition": lambda player, prop: player.argent >= prop.price + self.cash_buffer
            },
            "pay_jail": {
                "weight": 0.8 if difficulty == "hard" else 0.6 if difficulty == "medium" else 0.4,
                "condition": lambda player, game_round: player.argent >= 50 and game_round < 10
            },
            "build_house": {
                "weight": 0.7 if difficulty == "hard" else 0.5 if difficulty == "medium" else 0.3,
                "condition": lambda player, board: player.nb_proprietes >= 3 and player.argent >= 100 + self.cash_buffer
            }
        }
        self.load_weights()

    def choose_action(self, action_type, player, game_state, board):
        self.game_round = game_state.get("round", self.game_round + 1)
        rule = self.rules.get(action_type)
        if not rule:
            return False
        if rule["condition"](player, game_state.get("current_case", None) if action_type == "buy_property" else board if action_type == "build_house" else self.game_round):
            prob = rule["weight"] * (0.8 if self.difficulty == "hard" else 1.0 if self.difficulty == "medium" else 1.2)
            return random.random() < min(prob, 1.0)
        return False

    def evaluate_action(self, action_type, player, game_state, board):
        if action_type == "buy_property":
            if player.argent > 1000:  # Good: High cash after buying
                return 1
            if player.argent < 100:  # Bad: Low cash risks bankruptcy
                return -1
        elif action_type == "pay_jail" and not player.en_prison:
            return 1  # Good: Escaped jail to keep earning
        elif action_type == "build_house" and player.maisons > 0:
            return 1  # Good: Built a house, may increase rent
        return 0  # Neutral

    def update_weights(self, action_type, outcome):
        if action_type in self.rules:
            current_weight = self.rules[action_type]["weight"]
            self.rules[action_type]["weight"] = min(1.0, max(0.0, current_weight + self.learning_rate * outcome))
            self.save_weights()

    def save_weights(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        for action_type, rule in self.rules.items():
            cursor.execute("""
                INSERT INTO ai_weights (player_name, action_type, weight)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE weight = %s
            """, (self.AI_IDENTIFIER, action_type, rule["weight"], rule["weight"]))
        conn.commit()
        conn.close()

    def load_weights(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT action_type, weight FROM ai_weights WHERE player_name = %s", (self.AI_IDENTIFIER,))
        for action_type, weight in cursor.fetchall():
            if action_type in self.rules:
                self.rules[action_type]["weight"] = weight
        conn.close()


    def to_dict(self):
        return {
            'difficulty': self.difficulty,
            'weights': {k: v['weight'] for k, v in self.rules.items()}
        }

    @classmethod
    def from_dict(cls, data):
        ai = cls(difficulty=data['difficulty'])
        for action, weight in data['weights'].items():
            if action in ai.rules:
                ai.rules[action]['weight'] = weight
        return ai

class Case:
    def __init__(self, id, name, case_type, price, rent, owner):
        self.id = id
        self.name = name
        self.type = case_type
        self.price = price
        self.rent = rent
        self.owner = owner

class Joueur:
    def __init__(self, nom):
        self.nom = nom
        self.argent = 1500
        self.position = 0
        self.en_prison = False
        self.maisons = 0
        self.hotels = 0
        self.nb_proprietes = 0

    @classmethod
    def from_dict(cls, data):
        joueur = cls(data['nom'])
        joueur.argent = data['argent']
        joueur.position = data['position']
        joueur.en_prison = data['en_prison']
        joueur.maisons = data['maisons']
        joueur.hotels = data['hotels']
        joueur.nb_proprietes = data.get('nb_proprietes', 0)  # Ensure backward compatibility
        return joueur

    def to_dict(self):
        return {
            'nom': self.nom,
            'argent': self.argent,
            'position': self.position,
            'en_prison': self.en_prison,
            'maisons': self.maisons,
            'hotels': self.hotels,
            'nb_proprietes': self.nb_proprietes
        }

    def deplacer(self, deplacement):
        self.position = (self.position + deplacement) % NUM_CASES

def load_board_from_file(filename):
    board = []
    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            data = line.strip().split(',')
            board.append(Case(int(data[0]), data[1], data[2], int(data[3]), int(data[4]), int(data[5])))
    return board

def load_community_chest():
    cards = []
    with open("caisse.txt", "r", encoding="utf-8") as file:
        for line in file:
            data = line.strip().split(',')
            cards.append({'id': int(data[0]), 'description': data[1]})
    return cards

def load_chance_chest():
    cards = []
    with open("chance.txt", "r", encoding="utf-8") as file:
        for line in file:
            data = line.strip().split(',')
            cards.append({'id': int(data[0]), 'description': data[1]})
    return cards

@app.route('/')
def home():
    return render_template("plateformgaming.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            return render_template('dashboard.html', email=email)
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template('adminlogin.html')
@app.route('/log_ai', methods=['GET'])
def log_ai():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
    if session.get('username'):
        return redirect(url_for('play_ai'))
    session['next'] = 'play_ai'  # Store intent to play AI after login
    return render_template("log.html")
@app.route('/home')
def home_page():
    return render_template("home.html")

@app.route('/log', methods=['GET', 'POST'])
def log():
    if request.method == 'POST':
        username = request.form['username']
        session['username'] = username
        print("Utilisateur connecté :", username)
        # Redirect based on session['next'] or default to choose_players
        next_route = session.pop('next', 'choose_players')
        return redirect(url_for(next_route))
    return render_template("log.html")

@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, username, email, passwordhash, created_at FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT user_id, games_won FROM top_players ORDER BY games_won DESC LIMIT 10")
    top_players = cursor.fetchall()

    print("Top players:", top_players)

    cursor.execute("SELECT id, user_id, name, money, position, in_jail, houses, hotels, nb_properties, game_id FROM players")
    players = cursor.fetchall()

    cursor.close()
    conn.close()
    players = [p for p in players if p['name'] != "AI_Opponent"]
    return render_template('dashboard.html', users=users, top_players=top_players, players=players)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, username, email, passwordhash, created_at FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT user_id, games_won FROM top_players ORDER BY games_won DESC LIMIT 10")
    top_players = cursor.fetchall()

    print("Top players:", top_players)

    cursor.execute("SELECT id, user_id, name, money, position, in_jail, houses, hotels, nb_properties, game_id FROM players")
    players = cursor.fetchall()

    cursor.close()
    conn.close()
    players = [p for p in players if p['name'] != "AI_Opponent"]
    return render_template('dashboard.html', users=users, top_players=top_players, players=players)

@app.route('/choose_players', methods=['GET', 'POST'])
def choose_players():
    print("Session actuelle :", dict(session))
    if request.method == 'POST':
        nb_joueurs = int(request.form['nb_joueurs'])
        if 2 <= nb_joueurs <= MAX_JOUEURS:
            return redirect(url_for('fill_player_names', nb_joueurs=nb_joueurs))
        else:
            return render_template("choose_players.html", error="Le nombre de joueurs doit être entre 2 et 8.")
    print(session)
    return render_template("choose_players.html")

@app.route('/LoginPage')
def lg():
    return render_template("LoginPage.html")

@app.route('/logoutadmin')
def logoutadmin():
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    flash('You have been logged out.', 'info')
    return redirect(url_for('LoginPage'))

@app.route('/Myprofile')
def Profile():
    return render_template("Myprofile.html")

@app.route('/TopPlayers')
def Community():
    return render_template("TopPlayers.html")

@app.route('/sugnup')
def Sign():
    return render_template("signup.html")

@app.route('/games')
def games():
    return render_template("games.html")

@app.route('/contact')
def contact_page():
    return render_template("contact.html")

@app.route('/puzzel')
def puzzel_page():
    return render_template("puzzel.html")

@app.route('/aventure')
def aventure_page():
    return render_template("aventure.html")

@app.route('/strategie')
def strategie_page():
    return render_template("strategie.html")

@app.route('/action')
def action_page():
    return render_template("action.html")

@app.route('/play_ai', methods=['GET'])
def play_ai():
    username = session.get('username')
    print("USERNAME dans session :", username)

    if not username:
        session['next'] = 'play_ai'  # Store intent to play AI after login
        return redirect(url_for('log'))

    # Define the two players: human (username) and AI (AI_Opponent)
    joueurs_noms = [username, 'AI_Opponent']
    joueurs_types = ['human', 'ai']
    session['ia_round'] = 0
    # Save players to database
    conn = get_db_connection()
    cursor = conn.cursor()

    for nom in joueurs_noms:
        cursor.execute("""
            INSERT INTO players (name, money, position, in_jail, houses, hotels)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (nom, 1500, 0, 0, 0, 0))

    conn.commit()
    conn.close()

    # Initialize session with players
    joueurs_dicts = []
    for i, nom in enumerate(joueurs_noms):
        player_dict = {
            'nom': nom,
            'argent': 1500,
            'position': 0,
            'en_prison': False,
            'maisons': 0,
            'hotels': 0,
            'nb_proprietes': 0,
            'type': joueurs_types[i],
        }

        if joueurs_types[i] == 'ai':
            ai_instance = MonopolyLearningAI(difficulty="medium")
            player_dict['ai_state'] = ai_instance.to_dict()

        joueurs_dicts.append(player_dict)

    session['players'] = joueurs_dicts
    session['current_index'] = 0
    session['round'] = ia_round = 0
    print(ia_round)
    return redirect(url_for('game_ai', nb_joueurs=2))


@app.route('/fill_player_names/<int:nb_joueurs>', methods=['GET', 'POST'])
def fill_player_names(nb_joueurs):
    username = session.get('username')
    print("USERNAME dans session :", username)

    if not username:
        return redirect(url_for('log'))

    if request.method == 'POST':
        joueurs_noms = [username]
        for i in range(2, nb_joueurs + 1):
            nom = request.form.get(f'joueur_{i}')
            if nom:
                joueurs_noms.append(nom)

        conn = get_db_connection()
        cursor = conn.cursor()



        # Stocker la liste des joueurs sous forme de dictionnaires dans la session
        joueurs_dicts = []
        for nom in joueurs_noms:
            joueurs_dicts.append({
                'nom': nom,
                'argent': 1500,
                'position': 0,
                'en_prison': False,
                'maisons': 0,
                'hotels': 0,
                'nb_proprietes': 0
            })

        session['players'] = joueurs_dicts
        session['current_index'] = 0

        return redirect(url_for('game', nb_joueurs=nb_joueurs))

    return render_template("fill_player_names.html", nb_joueurs=nb_joueurs, first_player=username)


@app.route('/game/<int:nb_joueurs>', methods=['GET', 'POST'])
def game(nb_joueurs):
    joueurs_data = session.get('players', [])
    joueurs = [Joueur.from_dict(data) for data in joueurs_data]
    if not joueurs:
        return redirect(url_for('choose_players'))

    current_index = session.get('current_index', 0)
    current_player = joueurs[current_index]

    board = load_board_from_file("board.txt")
    community_chest_cards = load_community_chest()
    chance_cards = load_chance_chest()
    action_message = ""
    current_case = board[current_player.position]

    # Vérifier la victoire
    if current_player.argent >= GAIN:
        session['fin_de_jeu'] = f"{current_player.nom} a gagné avec {current_player.argent} Dinars!"
        session['resultats'] = [joueur.to_dict() for joueur in joueurs]
        return redirect(url_for('fin_de_jeu'))

    # Vérifie s'il y a une propriété en attente d'achat
    if session.get('pending_property'):
        decision = request.form.get('decision')
        case_index = session['pending_property']
        prop_case = board[case_index]

        if decision == 'oui':
            if current_player.argent >= prop_case.price:
                current_player.argent -= prop_case.price
                prop_case.owner = current_index
                current_player.nb_proprietes += 1
                action_message = f"{current_player.nom} a acheté {prop_case.name}."
            else:
                action_message = f"{current_player.nom} n'a pas assez d'argent pour acheter {prop_case.name}."
        else:
            action_message = f"{current_player.nom} a refusé d'acheter {prop_case.name}."

        session.pop('pending_property')
        session['current_index'] = (current_index + 1) % nb_joueurs
        joueurs[current_index] = current_player
        session['players'] = [joueur.to_dict() for joueur in joueurs]

        return render_template(
            "game.html",
            joueurs=[joueur.to_dict() for joueur in joueurs],
            current_player=current_player.to_dict(),
            current_case=prop_case,
            nbpropriete=current_player.nb_proprietes,
            action_message=action_message
        )

    if request.method == 'POST':
        if current_player.en_prison:
            decision = request.form.get('decision', default=0, type=int)
            if decision == 1 and current_player.argent >= JAIL_FINE:
                current_player.argent -= JAIL_FINE
                current_player.en_prison = False
                action_message = f"{current_player.nom} a payé {JAIL_FINE} Dinars pour sortir de prison."
            else:
                de1, de2 = random.randint(1, 6), random.randint(1, 6)
                if de1 == de2:
                    current_player.en_prison = False
                    current_player.deplacer(de1 + de2)
                    action_message = f"{current_player.nom} sort de prison avec un double ({de1}, {de2})."
                else:
                    action_message = f"{current_player.nom} reste en prison (dés : {de1}, {de2})."
        else:
            # Lancer les dés
            dice_roll = random.randint(1, 6) + random.randint(1, 6)
            previous_position = current_player.position
            current_player.deplacer(dice_roll)

            if previous_position > current_player.position or current_player.position == 0:
                current_player.argent += START_BONUS
                action_message = f"{current_player.nom} passe par la case départ et reçoit {START_BONUS} Dinars."

            current_case = board[current_player.position]

            # Propriété libre : attendre la décision
            if current_case.type == 'Propriete' and current_case.owner == -1:
                session['pending_property'] = current_player.position
                action_message = f"{current_player.nom} est sur {current_case.name}. Voulez-vous l'acheter pour {current_case.price} Dinars ?"

                joueurs[current_index] = current_player
                session['players'] = [joueur.to_dict() for joueur in joueurs]

                return render_template(
                    "game.html",
                    joueurs=[joueur.to_dict() for joueur in joueurs],
                    current_player=current_player.to_dict(),
                    current_case=current_case,
                    nbpropriete=current_player.nb_proprietes,
                    action_message=action_message
                )

            # Propriété appartenant à quelqu’un d’autre
            elif current_case.type == 'Propriete':
                owner = joueurs[current_case.owner]
                rent = current_case.rent
                if current_player.argent >= rent:
                    current_player.argent -= rent
                    owner.argent += rent
                    action_message = f"{current_player.nom} paye {rent} Dinars à {owner.nom} pour {current_case.name}."
                else:
                    action_message = f"{current_player.nom} n'a pas assez d'argent pour payer le loyer."

            # Caisse de communauté
            elif current_player.position in {2, 17, 33}:
                card_index = random.randint(0, NUM_CARTE_CAISSE - 1)
                card = community_chest_cards[card_index]
                action_message = f"{current_player.nom} tire une carte de Caisse: {card['description']}."
                apply_community_chest_card(current_player, card_index)

            # Chance
            elif current_player.position in {7, 22, 36}:
                card_index = random.randint(0, NUM_CARTE_CHANCE - 1)
                card = chance_cards[card_index]
                action_message = f"{current_player.nom} tire une carte de Chance: {card['description']}."
                apply_chance_card(current_player, card_index)

            # Aller en prison
            elif current_case.type == 'Prison' and current_player.position == 30:
                current_player.position = JAIL_POSITION
                current_player.en_prison = True
                action_message = f"{current_player.nom} est envoyé en prison."

            # Passer au joueur suivant
            if not current_player.en_prison:
                session['current_index'] = (current_index + 1) % nb_joueurs

            joueurs[current_index] = current_player
            session['players'] = [joueur.to_dict() for joueur in joueurs]

    return render_template(
        "game.html",
        joueurs=[joueur.to_dict() for joueur in joueurs],
        current_player=current_player.to_dict(),
        current_case=current_case,
        nbpropriete=current_player.nb_proprietes,
        action_message=action_message
    )

@app.route('/game_ai', methods=['GET', 'POST'])
def game_ai():
    joueurs_data = session.get('players', [])
    joueurs = [Joueur.from_dict(data) for data in joueurs_data]
    if not joueurs or len(joueurs) != 2:
        return redirect(url_for('play_ai'))

    current_index = session.get('current_index', 0)
    current_player = joueurs[current_index]

    if 'board' in session:
        board = [Case(*data) for data in session['board']]
    else:
        board = load_board_from_file("board.txt")
        session['board'] = [(c.id, c.name, c.type, c.price, c.rent, c.owner) for c in board]

    community_chest_cards = load_community_chest()
    chance_cards = load_chance_chest()
    action_message = ""

    # Initialize round counters if not present
    if 'player_rounds' not in session:
        session['player_rounds'] = [0] * len(joueurs)

    is_ai = joueurs_data[current_index].get('type') == 'ai'
    ai_instance = None
    if is_ai:
        ai_state = joueurs_data[current_index].get('ai_state')
        if ai_state:
            try:
                ai_instance = MonopolyLearningAI.from_dict(ai_state)
            except Exception as e:
                logger.error(f"Error deserializing AI state: {e}")
                ai_instance = MonopolyLearningAI()
        else:
            ai_instance = MonopolyLearningAI()
        logger.debug(f"AI state for {current_player.nom}: {ai_instance.to_dict()}")

    if current_player.argent >= GAIN:
        session['fin_de_jeu'] = f"{current_player.nom} a gagné avec {current_player.argent} Dinars!"
        session['resultats'] = [joueur.to_dict() for joueur in joueurs]
        logger.info(f"Game ended: {current_player.nom} won with {current_player.argent} dt")
        return redirect(url_for('fin_de_jeu'))

    # Define current_case at the start based on player's position
    current_case = board[current_player.position]

    if request.method == 'POST' or (is_ai and request.method == 'GET'):
        if current_player.en_prison:
            if is_ai:
                # Use the jail case explicitly for AI decisions
                jail_case = board[JAIL_POSITION]
                decision = ai_instance.choose_action("pay_jail", current_player, {
                    'current_case': jail_case,
                    'argent': current_player.argent
                }, board)
                if decision and current_player.argent >= JAIL_FINE:
                    current_player.argent -= JAIL_FINE
                    current_player.en_prison = False
                    action_message = f"{current_player.nom} a payé {JAIL_FINE} Dinars pour sortir de prison."
                    ai_instance.update_weights("pay_jail", ai_instance.evaluate_action("pay_jail", current_player, session, board))
                    logger.debug(f"AI paid jail fine: {current_player.argent} dt remaining")
                else:
                    de1, de2 = random.randint(1, 6), random.randint(1, 6)
                    if de1 == de2:
                        current_player.en_prison = False
                        current_player.deplacer(de1 + de2)
                        current_case = board[current_player.position]  # Update current_case after move
                        action_message = f"{current_player.nom} sort de prison avec un double ({de1}, {de2})."
                    else:
                        action_message = f"{current_player.nom} reste en prison (dés : {de1}, {de2})."
                    ai_instance.update_weights("jail_roll", ai_instance.evaluate_action("jail_roll", current_player, {
                        'success': de1 == de2,
                        'argent': current_player.argent
                    }, board))
                    logger.debug(f"AI jail roll: {de1}, {de2}, success={de1 == de2}")
            else:
                de1, de2 = random.randint(1, 6), random.randint(1, 6)
                if de1 == de2:
                    current_player.en_prison = False
                    current_player.deplacer(de1 + de2)
                    current_case = board[current_player.position]  # Update current_case after move
                    action_message = f"{current_player.nom} sort de prison avec un double ({de1}, {de2})."
                else:
                    action_message = f"{current_player.nom} reste en prison (dés : {de1}, {de2})."
        else:
            dice_roll = random.randint(1, 6) + random.randint(1, 6)
            previous_position = current_player.position
            current_player.deplacer(dice_roll)
            current_case = board[current_player.position]  # Update current_case after move

            if previous_position > current_player.position:
                current_player.argent += START_BONUS
                session['player_rounds'][current_index] += 1
                action_message = f"{current_player.nom} passe par la case départ et reçoit {START_BONUS} Dinars."
                logger.debug(f"Player {current_player.nom} passed start, rounds: {session['player_rounds'][current_index]}, argent: {current_player.argent} dt")

            if current_case.type == 'Propriete':
                if current_case.owner == -1:
                    if session['player_rounds'][current_index] >= 2:
                        if is_ai:
                            decision = ai_instance.choose_action("buy_property", current_player, {
                                'current_case': current_case,
                                'argent': current_player.argent
                            }, board)
                            if decision and current_player.argent >= current_case.price:
                                current_player.argent -= current_case.price
                                current_case.owner = current_index
                                current_player.nb_proprietes += 1
                                action_message = f"{current_player.nom} a acheté {current_case.name}."
                                ai_instance.update_weights("buy_property", ai_instance.evaluate_action("buy_property", current_player, session, board))
                                logger.debug(f"AI bought {current_case.name}, argent: {current_player.argent} dt")
                            else:
                                action_message = f"{current_player.nom} n'achète pas {current_case.name}."
                                logger.debug(f"AI declined to buy {current_case.name}")
                        else:
                            action_message = f"{current_player.nom} est sur {current_case.name} (peut acheter)."
                    else:
                        action_message = f"{current_player.nom} doit attendre {2 - session['player_rounds'][current_index]} tour(s) avant d'acheter."
                        logger.debug(f"Player {current_player.nom} cannot buy yet, rounds: {session['player_rounds'][current_index]}")
                elif current_case.owner != current_index:
                    owner = joueurs[current_case.owner]
                    # Use owner's maisons and hotels for rent calculation
                    rent = current_case.rent
                    if owner.maisons >= 4 and owner.hotels == 0:
                        rent *= 10  # 10x rent for 4+ houses
                    elif owner.hotels > 0:
                        rent *= 20  # 20x rent for any hotels
                    elif owner.maisons > 0:
                        rent *= (1 + owner.maisons * 2)  # 2x per house
                    if current_player.argent >= rent:
                        current_player.argent -= rent
                        owner.argent += rent
                        action_message = f"{current_player.nom} paye {rent} Dinars à {owner.nom}."
                        logger.debug(f"Player paid rent {rent} dt to {owner.nom}, argent: {current_player.argent} dt")
                    else:
                        action_message = f"{current_player.nom} est en faillite! Ne peut pas payer {rent} Dinars."
                        session['fin_de_jeu'] = f"{current_player.nom} a perdu (faillite)!"
                        session['resultats'] = [joueur.to_dict() for joueur in joueurs]
                        logger.info(f"Game ended: {current_player.nom} bankrupt")
                        return redirect(url_for('fin_de_jeu'))
                else:
                    action_message = f"{current_player.nom} est sur sa propriété {current_case.name}."

            elif current_player.position in {2, 17, 33}:
                card_index = random.randint(0, NUM_CARTE_CAISSE - 1)
                card = community_chest_cards[card_index]
                action_message = f"{current_player.nom} tire une carte de Caisse: {card['description']}."
                apply_community_chest_card(current_player, card_index)
                logger.debug(f"Player drew community chest card: {card['description']}, argent: {current_player.argent} dt")

            elif current_player.position in {7, 22, 36}:
                card_index = random.randint(0, NUM_CARTE_CHANCE - 1)
                card = chance_cards[card_index]
                action_message = f"{current_player.nom} tire une carte de Chance: {card['description']}."
                apply_chance_card(current_player, card_index)
                logger.debug(f"Player drew chance card: {card['description']}, argent: {current_player.argent} dt")

            elif current_case.type == 'Prison' and current_player.position == 30:
                current_player.position = JAIL_POSITION
                current_player.en_prison = True
                current_case = board[JAIL_POSITION]  # Update current_case to jail
                action_message = f"{current_player.nom} est envoyé en prison."
                logger.debug(f"Player sent to jail, position: {current_player.position}")

            if is_ai and not current_player.en_prison:
                # Check if AI can build houses or hotels
                owned_properties = [case for case in board if case.type == 'Propriete' and case.owner == current_index]
                can_build = current_player.nb_proprietes >= 3  # Proxy for owning a complete color group
                selected_property = owned_properties[0] if owned_properties else None

                if can_build and selected_property:
                    # Try to build a hotel if 4 houses
                    if current_player.maisons >= 4 and current_player.hotels < 4 and ai_instance.choose_action("build_hotel", current_player, {
                        'current_case': current_case,
                        'owned_properties': owned_properties,
                        'selected_property': selected_property,
                        'argent': current_player.argent
                    }, board):
                        if current_player.argent >= 80:
                            current_player.argent -= 80
                            current_player.hotels += 1
                            current_player.maisons -= 4
                            action_message += f" {current_player.nom} a construit un hôtel sur {selected_property.name}."
                            ai_instance.update_weights("build_hotel", ai_instance.evaluate_action("build_hotel", current_player, {
                                'current_case': current_case,
                                'owned_properties': owned_properties,
                                'selected_property': selected_property,
                                'argent': current_player.argent
                            }, board))
                            logger.debug(f"AI built hotel on {selected_property.name}, argent: {current_player.argent} dt")
                        else:
                            action_message += f" {current_player.nom} n'a pas assez d'argent pour construire un hôtel."
                            logger.debug(f"AI cannot afford hotel, argent: {current_player.argent} dt")
                    # Try to build a house
                    elif current_player.maisons < 4 and ai_instance.choose_action("build_house", current_player, {
                        'current_case': current_case,
                        'owned_properties': owned_properties,
                        'selected_property': selected_property,
                        'argent': current_player.argent
                    }, board):
                        if current_player.argent >= 50:
                            current_player.argent -= 50
                            current_player.maisons += 1
                            action_message += f" {current_player.nom} a construit une maison sur {selected_property.name}."
                            ai_instance.update_weights("build_house", ai_instance.evaluate_action("build_house", current_player, {
                                'current_case': current_case,
                                'owned_properties': owned_properties,
                                'selected_property': selected_property,
                                'argent': current_player.argent
                            }, board))
                            logger.debug(f"AI built house on {selected_property.name}, argent: {current_player.argent} dt")
                        else:
                            action_message += f" {current_player.nom} n'a pas assez d'argent pour construire une maison."
                            logger.debug(f"AI cannot afford house, argent: {current_player.argent} dt")
                    else:
                        action_message += f" {current_player.nom} ne construit pas (décision IA)."
                        logger.debug(f"AI declined to build house on {selected_property.name}")
                else:
                    action_message += f" {current_player.nom} ne peut pas construire (pas assez de propriétés)."
                    logger.debug(f"AI cannot build: owned_properties={len(owned_properties)}")

        session['current_index'] = (current_index + 1) % 2
        session['board'] = [(c.id, c.name, c.type, c.price, c.rent, c.owner) for c in board]

        joueurs[current_index] = current_player
        for i, joueur in enumerate(joueurs):
            joueurs_data[i].update(joueur.to_dict())
            if joueurs_data[i].get('type') == 'ai' and i == current_index and ai_instance:
                try:
                    joueurs_data[i]['ai_state'] = ai_instance.to_dict()
                except TypeError as e:
                    logger.error(f"Error serializing AI state: {e}")
                    joueurs_data[i]['ai_state'] = {}
        session['players'] = joueurs_data

        logger.debug(f"Player {current_player.nom} argent after turn: {current_player.argent} dt, properties: {current_player.nb_proprietes}")
        next_index = session['current_index']
        if session['players'][next_index]['type'] == 'ai':
            return redirect(url_for('game_ai'))

    return render_template(
        "game.html",
        joueurs=[joueur.to_dict() for joueur in joueurs],
        current_player=current_player.to_dict(),
        current_case=current_case,
        action_message=action_message,
        is_ai=is_ai
    )
def apply_community_chest_card(player, card_index):
    if card_index == 0:
        player.position = 0
        player.argent += 200
    elif card_index == 1:
        player.argent += 200
    elif card_index == 2:
        player.argent -= 50
    elif card_index == 3:
        player.argent += 50
    elif card_index == 5:
        player.position = JAIL_POSITION
        player.en_prison = True
    elif card_index == 6:
        player.argent += 100
    elif card_index == 7:
        player.argent += 100
    elif card_index == 8:
        player.argent -= 50
    elif card_index == 9:
        player.argent -= 150
    elif card_index == 10:
        player.argent += 25
    elif card_index == 11:
        player.argent += 100
    elif card_index == 12:
        player.argent += 100
    elif card_index == 13:
        player.argent += 50
    elif card_index == 14:
        player.argent -= (40 * player.maisons + 115 * player.hotels)

def apply_chance_card(player, card_index):
    if card_index == 0:
        player.position = 0
        player.argent += 200
    elif card_index == 1:
        player.argent += 150
    elif card_index == 2:
        player.argent -= 100
    elif card_index == 3:
        player.position += 3
    elif card_index == 4:
        player.position = JAIL_POSITION
        player.en_prison = True
    elif card_index == 5:
        player.argent += 50
    elif card_index == 6:
        player.argent -= 50
    elif card_index == 7:
        player.position -= 3
    elif card_index == 8:
        player.argent += 100
    elif card_index == 9:
        player.argent -= 150
    elif card_index == 10:
        player.argent += 25
    elif card_index == 11:
        player.argent += 75
    elif card_index == 12:
        player.argent -= 200
    elif card_index == 13:
        player.argent += 200
@app.route('/fin_de_jeu')
def fin_de_jeu():
    message_victoire = session.get('fin_de_jeu', None)
    resultats = session.get('resultats', [])
    joueurs_finaux = session.get('resultats', [])

    if not message_victoire or not joueurs_finaux:
        return render_template('fin_de_jeu.html', message_victoire="Erreur : Aucune donnée de victoire disponible.", resultats=[])

    # Connexion à la base de données
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert all players into the players table and track their IDs
    player_ids = {}
    for joueur in joueurs_finaux:
        cursor.execute("""
            INSERT INTO players (name, money, position, in_jail, houses, hotels)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            joueur['nom'],
            joueur['argent'],
            joueur['position'],
            int(joueur['en_prison']),
            joueur['maisons'],
            joueur['hotels']
        ))
        # Get the inserted player's ID
        player_ids[joueur['nom']] = cursor.lastrowid

    # Extract winner's name from message_victoire
    # Expected format: "{player_name} a gagné avec {amount} Dinars!"
    try:
        winner_name = message_victoire.split(" a gagné avec ")[0].strip()
    except (IndexError, AttributeError):
        conn.rollback()
        cursor.close()
        conn.close()
        return render_template('fin_de_jeu.html', message_victoire="Erreur : Impossible de déterminer le gagnant.", resultats=resultats)

    # Find the winner in joueurs_finaux
    winner = None
    for joueur in joueurs_finaux:
        if joueur['nom'] == winner_name:
            winner = joueur
            break

    if not winner:
        conn.rollback()
        cursor.close()
        conn.close()
        return render_template('fin_de_jeu.html', message_victoire="Erreur : Gagnant non trouvé dans les résultats.", resultats=resultats)

    # Insert winner's data into games_result
    game_id = 1
    if game_id is None:
        conn.rollback()
        cursor.close()
        conn.close()
        return render_template('fin_de_jeu.html', message_victoire="Erreur : ID de jeu manquant.", resultats=resultats)

    cursor.execute("""
        INSERT INTO game_results ( player_id, final_money, properties_owned, houses_built, hotels_built)
        VALUES ( %s, %s, %s, %s, %s)
    """, (

        player_ids[winner_name],
        winner['argent'],
        winner['nb_proprietes'],
        winner['maisons'],
        winner['hotels']
    ))

    # Commit the transaction
    conn.commit()

    # Close database resources
    cursor.close()
    conn.close()

    return render_template('fin_de_jeu.html', message_victoire=message_victoire, resultats=resultats)
@app.route('/recommencer', methods=['POST'])
def recommencer():
    session.pop('players', None)
    session.pop('current_index', None)
    session.pop('fin_de_jeu', None)
    session.pop('resultats', None)
    return redirect(url_for('choose_players'))

if __name__ == '__main__':
    app.run(debug=True)