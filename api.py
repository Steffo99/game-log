import flask as f
import flask_openid
from database import db as d
import database
import bcrypt
import re
import steam.webapi
import functools
# noinspection PyUnresolvedReferences
import configuration

app = f.Flask(__name__)
app.config.from_object("configuration.Config")
d.init_app(app)
steam_oid = flask_openid.OpenID(app)
steam_api = steam.WebAPI(app.config["STEAM_API_KEY"])


@app.after_request
def after_every_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


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
    user = d.session.query(database.User).filter_by(username=username).one_or_none()
    if user is not None:
        return f.jsonify({
            "result": "error",
            "reason": "Username already in use."
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


@app.route("/api/v1/user/token", methods=["POST"])
def api_v1_user_token():
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
    token = database.Token.new(user=db_user)
    d.session.add(token)
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "Logged in.",
        "user": db_user.json(),
        "token": token.token
    })


@app.route("/api/v1/user/search", methods=["GET"])
def api_v1_user_search():
    f_data = f.request.args
    user_id = f_data.get("user_id")
    username = f_data.get("username")
    if user_id:
        user = d.session.query(database.User).filter_by(user_id=user_id).one_or_none()
        if user is None:
            return f.jsonify({
                "result": "error",
                "reason": "No such user."
            })
        return f.jsonify({
            "result": "success",
            "description": "Retrieved user successfully."
            "user": db_user.json()
        })
    elif username:
        user = d.session.query(database.User).filter_by(username=username).one_or_none()
        if user is None:
            return f.jsonify({
                "result": "error",
                "reason": "No such user."
            })
        return f.jsonify({
            "result": "success",
            "description": "Retrieved user successfully."
            "user": db_user.json()
        })
    return f.jsonify({
        "result": "error",
        "reason": "Missing user_id or username."
    })


def login_required(func):
    @functools.wraps(func)
    def new_func(*args, **kwargs):
        token = f.request.form.get("token")
        if token is None:
            return f.jsonify({
                "result": "error",
                "reason": "No token specified."
            })
        login = d.session.query(database.Token).filter_by(token=token).one_or_none()
        if login is None:
            return f.jsonify({
                "result": "error",
                "reason": "Invalid token."
            })
        return func(user=login.user, *args, **kwargs)
    return new_func


@app.route("/api/v1/copy/add", methods=["POST"])
@login_required
def api_v1_copy_add(user):
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
    new_copy = database.Copy(owner_id=user.id)
    d.session.add(new_copy)
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "New copy created.",
        "copy": new_copy.json()
    })


@app.route("/api/v1/copy/progress", methods=["POST"])
@login_required
def api_v1_copy_progress(user):
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
    if copy.owner_id != user.id:
        return f.jsonify({
            "result": "error",
            "reason": "You don't own this copy."
        })
    progress = f_data.get("progress")
    if progress == "null":
        copy.progress = None
    elif progress not in database.GameProgress.__members__:
        return f.jsonify({
            "result": "error",
            "reason": "Invalid progress."
        })
    else:
        copy.progress = database.GameProgress[progress]
    d.session.commit()
    return f.jsonify({
        "result": "success",
        "description": "Copy progress updated.",
        "copy": copy.json()
    })


@app.route("/api/v1/copy/rating", methods=["POST"])
@login_required
def api_v1_copy_rating(user):
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
    if copy.owner_id != user.id:
        return f.jsonify({
            "result": "error",
            "reason": "You don't own this copy."
        })
    rating = f_data.get("rating")
    if rating == "null":
        copy.rating = None
    elif rating not in database.GameRating.__members__:
        return f.jsonify({
            "result": "error",
            "reason": "Invalid rating."
        })
    else:
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
    copies = d.session.query(database.Copy).filter_by(owner_id=user_id).order_by(database.Copy.rating.desc().nullslast()).all()
    return f.jsonify({
        "result": "success",
        "copies": [copy.json() for copy in copies]
    })


@app.route("/api/v1/copy/delete", methods=["POST"])
@login_required
def api_v1_copy_delete(user):
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
    if copy.owner_id != user.id:
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


@app.route("/api/v1/game/add", methods=["POST"])
@login_required
def api_v1_game_add(user):
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


@app.route("/openid/steam/login", methods=["GET"])
@steam_oid.loginhandler
def openid_steam_login():
    token = f.request.args.get("token")
    if token is None:
        return f.jsonify({
            "result": "error",
            "reason": "No token specified."
        })
    login = d.session.query(database.Token).filter_by(token=token).one_or_none()
    if login is None:
        return f.jsonify({
            "result": "error",
            "reason": "Invalid token."
        })
    f.session["user"] = login.user.json()
    f.session["openid_redirect_to"] = f.request.args.get("redirect_to")
    return steam_oid.try_login("http://steamcommunity.com/openid")


@steam_oid.after_login
def openid_steam_login_wait(response):
    user = f.session.get("user")
    if user["id"] is None:
        return f.jsonify({
            "result": "error",
            "reason": "Not logged in."
        })
    f.session["steam_id"] = re.match(r"https://steamcommunity.com/openid/id/(.*)", response.identity_url).group(1)
    return f.render_template("wait.html")


@app.route("/openid/steam/successful")
def openid_steam_login_successful():
    user = f.session.get("user")
    steam_id = f.session.get("steam_id")
    if user is None:
        return f.jsonify({
            "result": "error",
            "reason": "Not logged in."
        })
    if steam_id is None:
        return f.jsonify({
            "result": "error",
            "reason": "No steam login."
        })
    games_data = steam_api.IPlayerService.GetOwnedGames_v1(steamid=steam_id,
                                                           include_appinfo=True,
                                                           include_played_free_games=True,
                                                           appids_filter=None)
    # TODO: improve performance here
    for game in games_data["response"]["games"]:
        db_steamgame = d.session.query(database.SteamGame).filter_by(steam_app_id=game["appid"]).one_or_none()
        if db_steamgame is None:
            db_game = d.session.query(database.Game).filter(
                d.and_(
                    d.func.lower(database.Game.name) == game["name"].lower(),
                    database.Game.platform == "Steam"
                )
            ).one_or_none()
            if db_game is None:
                db_game = database.Game(name=game["name"],
                                        platform="Steam")
                d.session.add(db_game)
            db_steamgame = database.SteamGame(game=db_game,
                                              steam_app_id=game["appid"],
                                              steam_app_name=game["name"])
            d.session.add(db_steamgame)
        copy = d.session.query(database.SteamGame) \
            .filter_by(steam_app_id=game["appid"]) \
            .join(database.Game) \
            .join(database.Copy) \
            .filter_by(owner_id=user["id"]) \
            .first()
        if copy is not None:
            continue
        print(game["name"])
        if game["playtime_forever"] > 0:
            play_status = None
        else:
            play_status = database.GameProgress.NOT_STARTED
        d.session.flush()
        copy = database.Copy(owner_id=user["id"],
                             game_id=db_steamgame.game_id,
                             progress=play_status)
        d.session.add(copy)
    d.session.commit()
    return f.redirect(f.session.get("openid_redirect_to"))


if __name__ == "__main__":
    d.create_all(app=app)
    app.run()
