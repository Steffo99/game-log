import flask as f
from database import db as d
import database
import bcrypt

app = f.Flask(__name__)
app.secret_key = "indev"
d.init_app(app)


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
    bcrypted_password = bcrypt.hashpw(bytes(password), salt)
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
    if not bcrypt.checkpw(bytes(password), db_user.password):
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


@app.route("/api/v1/copy/add", methods=["POST"])
@login_required
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


@app.route("/api/v1/copy/progress", methods=["POST"])
@login_required
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


@app.route("/api/v1/copy/rating", methods=["POST"])
@login_required
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


@app.route("/api/v1/copy/delete", methods=["POST"])
@login_required
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
