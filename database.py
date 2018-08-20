import flask_sqlalchemy
import enum

db = flask_sqlalchemy.SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String)
    password = db.Column(db.LargeBinary)
    admin = db.Column(db.Boolean)

    def json(self):
        return {
            "id": self.id,
            "username": self.username,
            "password": "••••••"
        }


class Game(db.Model):
    __tablename__ = "games"

    name = db.Column(db.String)
    platform = db.Column(db.String)

    __table_args__ = [db.PrimaryKeyConstraint(name, platform)]

    def json(self):
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform
        }


class SteamGame(db.Model):
    __tablename__ = "steamgames"

    game_id = db.Column(db.BigInteger, db.ForeignKey("games.id"))
    game = db.relationship("games.id", lazy="joined")

    steam_app_id = db.Column(db.BigInteger, primary_key=True)
    steam_app_name = db.Column(db.String)

    def json(self):
        json = self.game.json()
        json["steam"] = {
            "app_id": self.steam_app_id,
            "app_name": self.steam_app_name
        }
        return json


class GameProgress(enum.Enum):
    NOT_STARTED = 0
    UNFINISHED = 1
    BEATEN = 2
    COMPLETED = 3
    MASTERED = 4
    NO_PROGRESS = 5


class GameRating(enum.Enum):
    UNRATED = 0
    DISLIKED = 1
    MIXED = 2
    LIKED = 3
    LOVED = 4


class Copy(db.Model):
    __tablename__ = "copies"

    id = db.Column(db.BigInteger, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    owner = db.relationship("users.id")
    game_id = db.Column(db.BigInteger)
    game = db.relationship("games.id")

    progress = db.Column(db.Enum(GameProgress))
    rating = db.Column(db.Enum(GameRating))

    def json(self):
        return {
            "id": self.id,
            "owner": self.owner.json(),
            "game": self.game.json(),
            "progress": self.progress,
            "rating": self.rating
        }