from enum import Enum


class ContentMediaType(Enum):
    IMAGE = "image_url"
    AUDIO = "audio_url"
    VIDEO = "video_url"
    UNKNOWN = "unknown"
    TEXT = "text"
    MEDIA = "media"


class MimeType(Enum):
    # Изображения
    PNG = "image/png"
    JPG = "image/jpeg"
    JPEG = "image/jpeg"
    GIF = "image/gif"
    BMP = "image/bmp"
    WEBP = "image/webp"
    SVG = "image/svg+xml"

    # Аудио
    MP3 = "audio/mpeg"
    WAV = "audio/wav"
    OGG = "audio/ogg"
    AAC = "audio/aac"
    M4A = "audio/mp4"
    FLAC = "audio/flac"

    # Видео
    MP4 = "video/mp4"
    AVI = "video/x-msvideo"
    MOV = "video/quicktime"
    WMV = "video/x-ms-wmv"
    FLV = "video/x-flv"
    WEBM = "video/webm"
    MKV = "video/x-matroska"


# Словарь расширений → (mime, тип)
EXTENSION_MAP: dict[str, tuple[str, ContentMediaType]] = {
    # Images
    "png": (MimeType.PNG.value, ContentMediaType.IMAGE),
    "jpg": (MimeType.JPG.value, ContentMediaType.IMAGE),
    "jpeg": (MimeType.JPEG.value, ContentMediaType.IMAGE),
    "gif": (MimeType.GIF.value, ContentMediaType.IMAGE),
    "bmp": (MimeType.BMP.value, ContentMediaType.IMAGE),
    "webp": (MimeType.WEBP.value, ContentMediaType.IMAGE),
    "svg": (MimeType.SVG.value, ContentMediaType.IMAGE),

    # Audio
    "mp3": (MimeType.MP3.value, ContentMediaType.AUDIO),
    "wav": (MimeType.WAV.value, ContentMediaType.AUDIO),
    "ogg": (MimeType.OGG.value, ContentMediaType.AUDIO),
    "aac": (MimeType.AAC.value, ContentMediaType.AUDIO),
    "m4a": (MimeType.M4A.value, ContentMediaType.AUDIO),
    "flac": (MimeType.FLAC.value, ContentMediaType.AUDIO),

    # Video
    "mp4": (MimeType.MP4.value, ContentMediaType.VIDEO),
    "avi": (MimeType.AVI.value, ContentMediaType.VIDEO),
    "mov": (MimeType.MOV.value, ContentMediaType.VIDEO),
    "wmv": (MimeType.WMV.value, ContentMediaType.VIDEO),
    "flv": (MimeType.FLV.value, ContentMediaType.VIDEO),
    "webm": (MimeType.WEBM.value, ContentMediaType.VIDEO),
    "mkv": (MimeType.MKV.value, ContentMediaType.VIDEO),
}

# Обратная карта MIME → тип контента
MIME_TYPE_MAP: dict[str, ContentMediaType] = {
    mime: media_type for mime, media_type in
    ((v[0], v[1]) for v in EXTENSION_MAP.values())
}