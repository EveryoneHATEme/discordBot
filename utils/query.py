import re


class Query:
    def __init__(self, args):
        self.body = " ".join(args).strip()

    def __bool__(self):
        return bool(self.body)

    def __str__(self):
        return self.body

    def get_yamusic_track_id(self):
        if not self.is_yamusic_track():
            raise QueryError('Query is not yamusic track')
        lst = self.body.split('/')
        return int(lst[-1]) if lst[-1] else int(lst[-2])

    def get_yamusic_album_id(self):
        if not self.is_yamusic_playlist():
            raise QueryError('Query is not yamusic playlist')
        lst = self.body.split('/')
        return int(lst[-1])

    def is_yt_video(self) -> bool:
        if re.match(r"(https?://)?(www\.)?youtu\.be|(https?://)?(www\.)?youtube\.com/watch\?v=", self.body):
            return True
        return False

    def is_yt_playlist(self) -> bool:
        if re.match(r"(https?://)?(www\.)?youtube\.com/playlist\?", self.body):
            return True
        return False

    def is_yamusic_playlist(self) -> bool:
        if re.match(r"(https?://)?(www\.)?music\.yandex\.ru/album/\d+($|/$)", self.body):
            return True
        return False

    def is_yamusic_track(self) -> bool:
        if re.match(r"(https?://)?(www\.)?music\.yandex\.ru/album/\d+/track/\d+($|/$)", self.body):
            return True
        return False

    def is_yamusic_user_playlist(self) -> bool:
        if re.match(r"(https?://)?(www\.)?music\.yandex\.ru/users/\w+/playlists/\d+($|/$)", self.body):
            return True
        return False


class QueryError(Exception):
    pass
