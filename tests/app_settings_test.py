from sts.config import get_app_settings, get_buckets_map, ImageSize, BucketSettings


def _assert_that_bucket_settings_are_equal(expected: BucketSettings, actual: BucketSettings):
    assert expected.alias == actual.alias
    assert expected.source_bucket == actual.source_bucket
    assert expected.life_time_days == actual.life_time_days
    assert expected.size == actual.size


_expected_thumbnail_small = BucketSettings(alias='small',
                                           size=ImageSize(300, 300),
                                           life_time_days=30,
                                           source_bucket='pictures')

_expected_thumbnail_medium = BucketSettings(alias='medium',
                                            size=ImageSize(500, 500),
                                            life_time_days=30,
                                            source_bucket='images')

_expected_thumbnail = BucketSettings(alias=None,
                                     size=ImageSize(100, 100),
                                     life_time_days=10,
                                     source_bucket='pictures')

_expected_pictures_small = BucketSettings(alias='p',
                                          size=ImageSize(50, 50),
                                          source_bucket='items',
                                          life_time_days=30)


def test_read():
    # arrange & act
    app_settings = get_app_settings()

    # assert
    assert app_settings
    # assert s3
    assert app_settings.s3.region == 'eu-west-1'
    assert app_settings.s3.use_tsl == False
    assert app_settings.s3.endpoint == 'localhost:9000'
    assert app_settings.s3.trust_cert == False
    assert app_settings.s3.access_key == 'MINIO_AK'
    assert app_settings.s3.secret_key == 'MINIO_SK'
    # assert size
    assert app_settings.size.w == 100
    assert app_settings.size.h == 100
    # assert source_bucket
    assert app_settings.source_bucket == 'pictures'

    # assert thumbnail-small
    bucket_settings = app_settings.buckets['thumbnail-small']
    _assert_that_bucket_settings_are_equal(_expected_thumbnail_small, bucket_settings)

    # assert thumbnail-medium
    bucket_settings = app_settings.buckets['thumbnail-medium']
    _assert_that_bucket_settings_are_equal(_expected_thumbnail_medium, bucket_settings)

    # assert thumbnail
    bucket_settings = app_settings.buckets['thumbnail']
    _assert_that_bucket_settings_are_equal(_expected_thumbnail, bucket_settings)

    # assert pictures-small
    bucket_settings = app_settings.buckets['pictures-small']
    _assert_that_bucket_settings_are_equal(_expected_pictures_small, bucket_settings)


def test_buckets_map():
    # arrange & act
    buckets_map = get_buckets_map()

    # assert
    assert buckets_map
    assert buckets_map.source_bucket == 'pictures'
    assert buckets_map.all_source_buckets == {'pictures', 'images', 'items'}
    assert buckets_map.alias_map == {'small': 'thumbnail-small', 'medium': 'thumbnail-medium', 'p': 'pictures-small'}

    # assert source bucket
    bucket_settings = buckets_map.buckets['pictures']
    _assert_that_bucket_settings_are_equal(BucketSettings(source_bucket='pictures', size=ImageSize(100, 100)),
                                           bucket_settings)

    # assert thumbnail-small bucket
    bucket_settings = buckets_map.buckets['thumbnail-small']
    _assert_that_bucket_settings_are_equal(_expected_thumbnail_small, bucket_settings)

    # assert thumbnail-medium
    bucket_settings = buckets_map.buckets['thumbnail-medium']
    _assert_that_bucket_settings_are_equal(_expected_thumbnail_medium, bucket_settings)

    # assert thumbnail
    bucket_settings = buckets_map.buckets['thumbnail']
    _assert_that_bucket_settings_are_equal(_expected_thumbnail, bucket_settings)

def test_uvicorn_defaults():
    # arrange & act
    app_settings = get_app_settings()

    # assert
    assert app_settings.uvicorn
    assert app_settings.uvicorn['host'] == '0.0.0.0'
    assert app_settings.uvicorn['port'] == 80
    assert app_settings.uvicorn['proxy_headers'] == True
    assert app_settings.uvicorn['workers'] == 4