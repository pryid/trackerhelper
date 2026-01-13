AUDIO_EXTS_DEFAULT = {
    ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma", ".aiff", ".aif", ".alac"
}

PREFERRED_GROUP_ORDER = ["Albums", "Singles"]
GROUP_TITLES = {
    "ru": {
        "Albums": "Альбомы",
        "Singles": "Синглы",
    },
    "en": {
        "Albums": "Albums",
        "Singles": "Singles",
    },
}

BBCODE_LABELS = {
    "ru": {
        "genre": "Жанр",
        "media": "Носитель",
        "label": "Издатель (лейбл)",
        "year": "Год издания",
        "codec": "Аудиокодек",
        "rip_type": "Тип рипа",
        "source": "Источник",
        "duration": "Продолжительность",
        "tracklist": "Треклист",
        "dr_report": "Динамический отчет (DR)",
        "about": "Об исполнителе (группе)",
        "label_placeholder": "ЛЕЙБЛ",
    },
    "en": {
        "genre": "Genre",
        "media": "Media",
        "label": "Label",
        "year": "Year",
        "codec": "Audio codec",
        "rip_type": "Rip type",
        "source": "Source",
        "duration": "Duration",
        "tracklist": "Tracklist",
        "dr_report": "Dynamic Range report (DR)",
        "about": "About the artist (group)",
        "label_placeholder": "LABEL",
    },
}

TAG_KEYS_ALBUM = ["album"]
TAG_KEYS_ALBUM_ARTIST = ["album_artist", "albumartist"]
TAG_KEYS_ARTIST = ["artist", "performer"]

PLACEHOLDER_GENRE = "GENRE"
PLACEHOLDER_ROOT_COVER = "ROOT_COVER_URL"
PLACEHOLDER_COVER = "COVER_URL"
PLACEHOLDER_INFO = "info"
PLACEHOLDER_YEAR = "YEAR"
PLACEHOLDER_TITLE = "TITLE"
PLACEHOLDER_DURATION = "00:00:00"
PLACEHOLDER_MEDIA = "WEB [url=https://service.com/123]Service[/url]"
PLACEHOLDER_RIP_TYPE = "tracks"
PLACEHOLDER_SOURCE = "WEB"
