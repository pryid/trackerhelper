AUDIO_EXTS_DEFAULT = {
    ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma", ".aiff", ".aif", ".alac"
}

PREFERRED_GROUP_ORDER = ["Albums", "Singles"]
GROUP_TITLES = {
    "ru": {
        "Albums": "\u0410\u043b\u044c\u0431\u043e\u043c\u044b",
        "Singles": "\u0421\u0438\u043d\u0433\u043b\u044b",
    },
    "en": {
        "Albums": "Albums",
        "Singles": "Singles",
    },
}

BBCODE_LABELS = {
    "ru": {
        "genre": "\u0416\u0430\u043d\u0440",
        "media": "\u041d\u043e\u0441\u0438\u0442\u0435\u043b\u044c",
        "label": "\u0418\u0437\u0434\u0430\u0442\u0435\u043b\u044c (\u043b\u0435\u0439\u0431\u043b)",
        "year": "\u0413\u043e\u0434 \u0438\u0437\u0434\u0430\u043d\u0438\u044f",
        "codec": "\u0410\u0443\u0434\u0438\u043e\u043a\u043e\u0434\u0435\u043a",
        "rip_type": "\u0422\u0438\u043f \u0440\u0438\u043f\u0430",
        "source": "\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a",
        "duration": "\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0441\u0442\u044c",
        "tracklist": "\u0422\u0440\u0435\u043a\u043b\u0438\u0441\u0442",
        "dr_report": "\u0414\u0438\u043d\u0430\u043c\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043e\u0442\u0447\u0435\u0442 (DR)",
        "about": "\u041e\u0431 \u0438\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u0435 (\u0433\u0440\u0443\u043f\u043f\u0435)",
        "label_placeholder": "\u041b\u0415\u0419\u0411\u041b",
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
