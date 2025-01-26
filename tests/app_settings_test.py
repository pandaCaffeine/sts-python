from sts.config import get_app_settings, get_buckets_map, ImageSize


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
    assert bucket_settings
    assert bucket_settings.alias == 'small'
    assert bucket_settings.source_bucket == 'pictures'
    assert bucket_settings.life_time_days == 30
    assert bucket_settings.size.w == 300
    assert bucket_settings.size.h == 300

    # assert thumbnail-medium
    bucket_settings = app_settings.buckets['thumbnail-medium']
    assert bucket_settings
    assert bucket_settings.alias == 'medium'
    assert bucket_settings.source_bucket == 'images'
    assert bucket_settings.life_time_days == 30
    assert bucket_settings.size.w == 500
    assert bucket_settings.size.h == 500

    # assert thumbnail
    bucket_settings = app_settings.buckets['thumbnail']
    assert bucket_settings
    assert not bucket_settings.alias
    assert bucket_settings.source_bucket == 'pictures'
    assert bucket_settings.life_time_days == 10
    assert bucket_settings.size.w == 100
    assert bucket_settings.size.h == 100

def test_buckets_map():
    # arrange & act
    buckets_map = get_buckets_map()

    # assert
    assert buckets_map
    assert buckets_map.source_bucket == 'pictures'
    assert buckets_map.all_source_buckets == {'pictures', 'images'}
    assert buckets_map.alias_map == { 'small': 'thumbnail-small', 'medium': 'thumbnail-medium' }

    # assert source bucket
    bucket_settings = buckets_map.buckets['pictures']
    assert bucket_settings.source_bucket == 'pictures'
    assert bucket_settings.size == ImageSize(100, 100)

    # assert thumbnail-small bucket
    bucket_settings = buckets_map.buckets['thumbnail-small']
    assert bucket_settings.alias == 'small'
    assert bucket_settings.source_bucket == 'pictures'
    assert bucket_settings.life_time_days == 30
    assert bucket_settings.size.w == 300
    assert bucket_settings.size.h == 300

    # assert thumbnail-medium
    bucket_settings = buckets_map.buckets['thumbnail-medium']
    assert bucket_settings
    assert bucket_settings.alias == 'medium'
    assert bucket_settings.source_bucket == 'images'
    assert bucket_settings.life_time_days == 30
    assert bucket_settings.size.w == 500
    assert bucket_settings.size.h == 500

    # assert thumbnail
    bucket_settings = buckets_map.buckets['thumbnail']
    assert bucket_settings
    assert not bucket_settings.alias
    assert bucket_settings.source_bucket == 'pictures'
    assert bucket_settings.life_time_days == 10
    assert bucket_settings.size.w == 100
    assert bucket_settings.size.h == 100





