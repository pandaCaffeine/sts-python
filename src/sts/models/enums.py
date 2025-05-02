from enum import StrEnum, IntEnum


class ImageFormat(StrEnum):
    """ Supported file formats """

    NONE = 'none'
    """ Unspecified file format - use source file format """
    PNG = 'png'
    """ PNG """
    JPEG = 'jpeg'
    """ JPEG """


class BucketStatus(StrEnum):
    """ Bucket status """

    created = 'created'
    """ The bucket was just created """
    exists = 'exists'
    """ The bucket already exists """
    error = 'error'
    """ Failed to create bucket """


class ScanStatus(IntEnum):
    BUCKET_NOT_FOUND = 1
    SOURCE_FILE_NOT_FOUND = 2
    USE_SOURCE_FILE = 3
    FILE_FOUND = 4
    CREATE_NEW = 5
