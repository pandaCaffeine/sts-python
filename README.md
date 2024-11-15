<img src="assets/logo.png">

# Simple Thumbnail Service (sts)

The microservice serves thumbnail images in `minio` and does some ✨magic for you:

* Creates buckets on startup if they absent.
* Creates optimized thumbnails on demand which saves bytes in your file storage.
* Uses lifecycle rules to manage thumbnail files.

## Key features

* Etag support to minimize traffic between the browser and the server.
* Customizable: multiple thumbnail buckets can be configured, with options for one or a few buckets for source images.
* Multiple image formats - `sts` uses the `pillow` library to manipulate image files.
* Optimized thumbnails: all created thumbnail files are optimized with specific encoding settings.

## Used libraries

1. `pillow` - for processing image files
2. `fastapi` - web framework
3. `loguru` - for logging
4. `pydantic-settings` - for reading settings

## Installation

Use docker image `pandacaffeine/sts:1.1.0` in your docker environment or docker-compose.

## Algorithm
1. Query the object stat from minio for the source file. If the file is not found, return a 404 response.
2. Query the object stat for the thumbnail file requested.
3. Check if the thumbnail file exists in minio. If it does:
   - Check if the parent-etag of the thumbnail is equal to the source file's etag. If not, go to step 4.
   - If the HTTP request has an If-None-Match header, check if its value is equal to the file's stats. If so, return a 304 response and exit.
4. Return the thumbnail file with an Etag header from minio and exit.
5. Try to generate a thumbnail file.
6. Save the generated thumbnail into minio.
7. Return the created thumbnail.

## Configuration

`sts` uses `pydantic-settings` to read configuration from `ENV` variables. Symbols `__` is used as nested objects
delimiter.

### Scheme for example

```json
{
  "s3": {
    "endpoint": "localhost:9000",
    "access_key": "MINIO_AK",
    "secret_key": "MINIO_SK",
    "region": "eu-west-1",
    "use_tsl": false,
    "trust_cert": true
  },
  "buckets": {
    "thumbnail": {
      "width": 200,
      "height": 200,
      "life_time_days": 30,
      "source_bucket": null,
      "alias": null
    }
  },
  "source_bucket": "images",
  "log_level": "INFO",
  "log_fmt": "{time} | {level}: {extra} {message}"
}
```

#### Root configs

`s3` - connection configs to file storage. Only `minio` was tested.
`buckets` - map of buckets in `minio` the will hold thumbnails.
`source_bucket` - default bucket that holds your origin images. Can be overridden for each thumbnail bucket.
`log_level` - logging level for `loguru`.
`log_fmt` - logging pattern for `logur`.

#### S3 configs

`endpoint` - address to `minio`.
`access_key` - access key for `minio`.
`secret_key` - secret key for `minio`.
`region` - used region.
`use_tls` - set `true` to use HTTPS connection, `false` by default.
`trust_cert` - set `true` to skip certificate check for HTTPS connection, `true` by default.

#### Buckets configs

`buckets` is dictionary (map) where each key is bucket name and value is bucket configuration, so key must be valid
bucket name.
`width` - desired thumbnail width (int).
`height` - desired thumbnail height (int).
`life_time_days` - how many days thumbnail files are kept in the bucket, default value is `30` days. Set to zero to keep
them infinity.
`source_bucket` - overrides root `source_bucket`, so you can define thumbnail buckets for few buckets with original
files. If this config is not set - the root `source_bucket` will be used.
`alias` - an optional alias for the bucket, used for alternative endpoint (see below).

### ENV configuration

To set configuration use environment variables in docker image or provide `.env` file in the `/app` directory of an
image.

#### .env file example

```
source_bucket=images  
buckets__thumbnail__width=200  
buckets__thumbnail__height=200  
buckets__thumbnail__alias=small
```

In example above configuration of `source_bucket` is set to `images` and new thumbnail bucket add with following
configuration:

* name is set to `thumbnail`
* desired width is set to `200` pixels
* desired height is set to `200` pixels
* alias is set to `small`

## Endpoints

`sts` provides 4 endpoints:

1. `/{bucket}/{filename}` - direct access to the thumbnail file, this endpoint is considered as main.
2. `/{sourcebucket}/{filename}/{alias}` - an alternative endpoint that leads to thumbnail file by its alias
3. `/hc` - health check endpoint
4. `/health` - alternative route for the `/hc` route

## Example

Let's imagine that we have some web application on host `office.net`, and additional host `images.office.net` which
serves image files for a client:

<img src="assets/example_scheme.png">

In the given example `backend` serves all user requests (API) and manipulates `images` bucket (which stores original
image files) while `sts` can read files from `images` bucket and creates thumbnails for the source images.

### Playground

The repository contains an example nginx configuration file and a docker-compose file that you can use to run locally:

1. go to `plaground` dir: `cd playground`
2. build docker compose: `docker compose build`
3. run docker compose: `docker compose up -d`
4. open minio console in browser: `http://localhost:9001` and login with following credentials:
    1. username: `MINIO_AK`
    2. password: `MINIO_SK`
5. upload any image into `images` bucket
6. test in browser small thumbnail: `http://localhost/images/{file_name}/small`
7. test in browser medium thumbnail: `http://localhost/images/{file_name}/medium`

## Roadmap

There are no specific deadlines at this time, but we have some ideas for future development:

1. ✅ version 1.1: source file first - return 404 if source file was deleted, recreate thumbnail file if source file was
   changed
2. 🔳 version 1.2: file configuration for thumbnails - ability to choose thumbnails file format and some options like
   quality
3. 🔳 version 2.0: refactoring, fixes, code cleanup