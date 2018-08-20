import flask as f
import flask_openid
from database import db as d
import database
import bcrypt
import re
import steam.webapi
import json
# noinspection PyUnresolvedReferences
import configuration

app = f.Flask(__name__)
app.config.from_object("configuration.Config")
d.init_app(app)
steam_oid = flask_openid.OpenID(app)
steam_api = steam.WebAPI(app.config["STEAM_API_KEY"])


@app.route("/api/v1/user/register", methods=["POST"])
def api_v1_user_register():
    f_data = f.request.form
    username = f_data.get("username")
    password = f_data.get("password")
    if username is None or password is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing username or password."
        })
    salt = bcrypt.gensalt()
    bcrypted_password = bcrypt.hashpw(bytes(password, encoding="utf8"), salt)
    new_user = database.User(username=username,
                             password=bcrypted_password,
                             admin=False)
    d.session.add(new_user)
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "New user created.",
        "user": new_user.json()
    })


@app.route("/api/v1/user/login", methods=["POST"])
def api_v1_user_login():
    f_data = f.request.form
    username = f_data.get("username")
    password = f_data.get("password")
    if username is None or password is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing username or password."
        })
    db_user = d.session.query(database.User).filter_by(username=username).one_or_none()
    if db_user is None:
        return f.jsonify({
            "result": "error",
            "reason": "No such user."
        })
    if not bcrypt.checkpw(bytes(password, encoding="utf8"), db_user.password):
        return f.jsonify({
            "result": "error",
            "reason": "Invalid password."
        })
    f.session["username"] = db_user.username
    f.session["user_id"] = db_user.id
    f.session["admin"] = db_user.admin
    return f.jsonify({
        "result": "success",
        "description": "Logged in.",
        "user": db_user.json()
    })


def login_required(func):
    def new_func(*args, **kwargs):
        user_id = f.session.get("user_id")
        if user_id is None:
            return f.jsonify({
                "result": "error",
                "reason": "Not logged in."
            })
        return func(user_id=user_id, *args, **kwargs)


def admin_required(func):
    def new_func(*args, **kwargs):
        admin = f.session.get("admin")
        if not admin:
            return f.jsonify({
                "result": "error",
                "reason": "Insufficient permissions."
            })
        return func(*args, **kwargs)


@login_required
@app.route("/api/v1/copy/add", methods=["POST"])
def api_v1_copy_add(user_id):
    f_data = f.request.form
    game_id = f_data.get("game_id")
    if game_id is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing game_id."
        })
    game = d.session.query(database.Game).filter_by(id=game_id).one_or_none()
    if game is None:
        return f.jsonify({
            "result": "error",
            "reason": "No such game."
        })
    new_copy = database.Copy(owner_id=user_id)
    d.session.add(new_copy)
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "New copy created.",
        "copy": new_copy.json()
    })


@login_required
@app.route("/api/v1/copy/progress", methods=["POST"])
def api_v1_copy_progress(user_id):
    f_data = f.request.form
    copy_id = f_data.get("copy_id")
    if copy_id is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing copy_id."
        })
    copy = d.session.query(database.Copy).filter_by(id=copy_id).one_or_none()
    if copy is None:
        return f.jsonify({
            "result": "error",
            "reason": "No such copy."
        })
    if copy.owner_id != user_id:
        return f.jsonify({
            "result": "error",
            "reason": "You don't own this copy."
        })
    progress = f_data.get("progress")
    if progress is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing progress."
        })
    if progress not in database.GameProgress.__members__:
        return f.jsonify({
            "result": "error",
            "reason": "Invalid progress."
        })
    copy.progress = database.GameProgress[progress]
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "Copy progress updated.",
        "copy": copy.json()
    })


@login_required
@app.route("/api/v1/copy/rating", methods=["POST"])
def api_v1_copy_rating(user_id):
    f_data = f.request.form
    copy_id = f_data.get("copy_id")
    if copy_id is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing copy_id."
        })
    copy = d.session.query(database.Copy).filter_by(id=copy_id).one_or_none()
    if copy is None:
        return f.jsonify({
            "result": "error",
            "reason": "No such copy."
        })
    if copy.owner_id != user_id:
        return f.jsonify({
            "result": "error",
            "reason": "You don't own this copy."
        })
    rating = f_data.get("rating")
    if rating is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing progress."
        })
    if rating not in database.GameRating.__members__:
        return f.jsonify({
            "result": "error",
            "reason": "Invalid progress."
        })
    copy.rating = database.GameRating[rating]
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "Copy rating updated.",
        "copy": copy.json()
    })


@app.route("/api/v1/copy/list", methods=["GET"])
def api_v1_copy_list():
    f_data = f.request.args
    user_id = f_data.get("user_id")
    if user_id is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing user_id."
        })
    copies = d.session.query(database.Copy).filter_by(owner_id=user_id).all()
    return f.jsonify({
        "result": "success",
        "copies": [copy.json() for copy in copies]
    })


@login_required
@app.route("/api/v1/copy/delete", methods=["POST"])
def api_v1_copy_delete(user_id):
    f_data = f.request.form
    copy_id = f_data.get("copy_id")
    if copy_id is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing copy_id."
        })
    copy = d.session.query(database.Copy).filter_by(id=copy_id).one_or_none()
    if copy is None:
        return f.jsonify({
            "result": "error",
            "reason": "No such copy."
        })
    if copy.owner_id != user_id:
        return f.jsonify({
            "result": "error",
            "reason": "You don't own this copy."
        })
    d.session.remove(copy)
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "Copy deleted.",
        "copy": copy.json()
    })


@login_required
@app.route("/api/v1/game/add", methods=["POST"])
def api_v1_game_add(user_id):
    f_data = f.request.form
    name = f_data.get("game_name")
    platform = f_data.get("game_platform")
    if name is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing game_name."
        })
    if platform is None:
        return f.jsonify({
            "result": "error",
            "reason": "Missing game_platform."
        })
    game = d.session.query(database.Game).filter(
        d.and_(
            d.func.lower(database.Game.name) == name.lower(),
            d.func.lower(database.Game.platform) == platform.lower()
        )
    ).one_or_none()
    if game is not None:
        return f.jsonify({
            "result": "error",
            "reason": "Game already exists.",
            "game": game.json()
        })
    game = database.Game(name=name,
                         platform=platform)
    d.session.add(game)
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "Game added.",
        "game": game.json()
    })


@app.route("/openid/steam/login")
@steam_oid.loginhandler
def api_v1_steam_login():
    return steam_oid.try_login("http://steamcommunity.com/openid")


@steam_oid.after_login
def api_v1_steam_login_successful(response):
    user_id = f.session.get("user_id")
    if user_id is None:
        return f.jsonify({
            "result": "error",
            "reason": "Not logged in."
        })
    steam_id = re.match(r"https://steamcommunity.com/openid/id/(.*)", response.identity_url).group(1)
    games_data = steam_api.IPlayerService.GetOwnedGames_v1(steamid=steam_id,
                                                           include_appinfo=True,
                                                           include_played_free_games=True,
                                                           appids_filter=None)
    for game in games_data["response"]["games"]:
        db_steamgame = d.session.query(database.SteamGame).filter_by(steam_app_id=game["appid"]).one_or_none()
        if db_steamgame is None:
            copy = d.session.query(database.Copy) \
                .filter_by(owner_id=user_id) \
                .join(database.Game) \
                .join(database.SteamGame) \
                .filter_by(steam_app_id=game["appid"]) \
                .first()
            if copy is not None:
                continue
            db_game = d.session.query(database.Game).filter(
                d.and_(
                    d.func.lower(database.Game.name) == game["name"].lower(),
                    database.Game.platform == "PC"
                )
            ).one_or_none()
            if db_game is None:
                db_game = database.Game(name=game["name"],
                                        platform="PC")
                d.session.add(db_game)
            db_steamgame = database.SteamGame(game=db_game,
                                              steam_app_id=game["appid"],
                                              steam_app_name=game["name"])
            d.session.add(db_steamgame)
        if game["playtime_forever"] > 0:
            play_status = None
        else:
            play_status = database.GameProgress.NOT_STARTED
        d.session.flush()
        copy = database.Copy(owner_id=user_id,
                             game_id=db_steamgame.game_id,
                             progress=play_status)
        d.session.add(copy)
    d.session.commit()
    return f.redirect("/")


if __name__ == "__main__":
    d.create_all(app=app)
    app.run()