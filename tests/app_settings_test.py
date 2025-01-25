from sts.config import get_app_settings


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
