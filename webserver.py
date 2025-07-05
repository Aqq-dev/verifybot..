from flask import Flask, redirect, request, render_template, session
import requests, os, json

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = "https://verifyfreak.onrender.com/callback"
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
DB_FILE = "db.json"
TOKENS_FILE = "access_tokens.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "w") as f:
            json.dump({}, f)
    with open(TOKENS_FILE, "r") as f:
        return json.load(f)

def save_tokens(data):
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/oauth")
def oauth():
    uid = request.args.get("uid")
    role = request.args.get("role")
    return redirect(
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20email%20guilds.join%20email&state={uid}:{role}"
    )

@app.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")
    uid, role = state.split(":")
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify email guilds.join email'
    }

    r = requests.post('https://discord.com/api/oauth2/token', data=data)
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    user_info = requests.get("https://discord.com/api/users/@me", headers=headers).json()

    email = user_info.get("email")
    user_id = user_info.get("id")

    db = load_db()
    for entry in db:
        if entry["ip"] == ip:
            return render_template("error.html", reason="このIPは既に使用されています。")

    db.append({"ip": ip, "email": email, "user_id": user_id})
    save_db(db)

    tokens = load_tokens()
    tokens[user_id] = token
    save_tokens(tokens)

    requests.put(
        f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}",
        headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"},
        json={"access_token": token}
    )

    requests.put(
        f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}/roles/{role}",
        headers={"Authorization": f"Bot {BOT_TOKEN}"}
    )

    return render_template("success.html", username=user_info.get("username"))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")

    if not session.get("admin"):
        return '''
        <form method="POST">
            <input type="password" name="password" placeholder="Password">
            <button type="submit">ログイン</button>
        </form>
        '''

    users = load_db()
    return render_template("admin.html", users=users)

@app.route("/tokens", methods=["GET", "POST"])
def tokens():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/tokens")
    if not session.get("admin"):
        return '''
        <form method="POST">
            <input type="password" name="password" placeholder="Password">
            <button type="submit">ログイン</button>
        </form>
        '''
    with open("access_tokens.json", "r") as f:
        tokens = json.load(f)
    return f"<pre style='background:#111;color:#0f0;padding:10px'>{json.dumps(tokens, indent=2)}</pre>"
