<img src="assets/logo.png">

# Simple Thumbnail Service (sts)

Current version: `1.2`

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

Use docker image `pandacaffeine/sts:1.2.0` in your docker environment or docker-compose.

## Algorithm

1. Query the object stat from minio for the source file. If the file is not found, return a 404 response.
2. Query the object stat for the thumbnail file requested.
3. Check if the thumbnail file exists in minio. If it does:
    - Check if the parent-etag of the thumbnail is equal to the source file's etag. If not, go to step 4.
    - If the HTTP request has an If-None-Match header, check if its value is equal to the file's stats. If so, return a
      304 response and exit.
4. Return the thumbnail file with an Etag header from minio and exit.
5. Try to generate a thumbnail file.
6. Save the generated thumbnail into minio.
7. Return the created thumbnail.

## Configuration

`sts` uses `pydantic-settings` to read configuration from `ENV` variables. Symbols `__` is used as nested objects
delimiter.

Alternative way to configure service:

1. `config.json` file
2. `.env` file

Configuration files must be places inside image in folder `/code/`.

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

The `s3` and `buckets` sections can be set as string values. The following example is equivalent to the JSON example
above:

```yaml
environment:
  S3: http://MINIO_AK:MINIO_SK@localhost:9000/eu-west-1/images
  BUCKETS__THUMBNAIL: size=200x200&life_time_days=30
  LOG_LEVEL: INFO
  LOG_FMT: '{time} | {level}: {extra} {message}'
```

#### Root configs

* `s3` - connection configs to file storage. Only `minio` was tested.
* `buckets` - map of buckets in `minio` the will hold thumbnails.
* `source_bucket` - default bucket that holds your origin images. Can be overridden for each thumbnail bucket. This
  config is optional.
* `log_level` - logging level for `loguru`.
* `log_fmt` - logging pattern for `loguru`.

##### uvicorn specific settings
You can set uvicorn specific settings in `uvicorn` section, default value is:
```json
{
  "uvicorn": {
    "host": "0.0.0.0",
    "port": 80,
    "proxy_headers": true
  }
}
```
You can set all settings according to the official docs https://www.uvicorn.org/settings/.

In most cases you may want to set following uvicorn settings:
* `host` - bind socket to this host. Use `0.0.0.0` to make the application available on your local network. IPv6 addresses are supported, for example: `::`. Default: `0.0.0.0` (overridden in sts).
* `port` - bind to a socket with this port. Default: `80` (overridden on sts).
* `workers` - use multiple worker processes. Defaults to the `$WEB_CONCURRENCY` environment variable if available, or 1.
* `access_log` - enables access log. Use `False` to disable access log only, without changing log level  Default: `True`.
* `log_level` - set the log level. Options: `critical`, `error`, `warning`, `info`, `debug`, `trace`. Default: `info`.


#### S3 configs

* `endpoint` - address to `minio`.
* `access_key` - access key for `minio`.
* `secret_key` - secret key for `minio`.
* `region` - used region.
* `use_tls` - set `true` to use HTTPS connection, `false` by default.
* `trust_cert` - set `true` to skip certificate check for HTTPS connection, `true` by default.

The `s3` section can be set as HTTP url with following pattern:

```
{scheme}://{access_key}:{secret_key}@{host}:{port}/{region}/{source_bucket}
```

* `{scheme}` - `https` value is equivalent to `use_tsl: true` and `trust_cert: true`. Set to `http` if you trust host.
* `{source_bucket}` is optional value, the root `source_bucket` config has higher priority.

The rest parameters have the same meaning as it described in S3 configs section.

#### Buckets configs

* `buckets` is dictionary (map) where each key is bucket name and value is bucket configuration, so key must be valid
  bucket name.
* `size` - desired thumbnail size in pixels, can be set as string with following format: `{width}x{height}`. Nested
  configs:
    * `width` - desired thumbnail width (int).
    * `height` - desired thumbnail height (int).
* `life_time_days` - how many days thumbnail files are kept in the bucket, default value is `30` days. Set to zero to
  keep
  them infinity.
* `source_bucket` - overrides root `source_bucket`, so you can define thumbnail buckets for few buckets with original
  files. If this config is not set - the root `source_bucket` will be used.
* `alias` - an optional alias for the bucket, used for alternative endpoint (see below).

The bucket config can set as string value in http query-like way, for example:

```
alias=image&size=200x200&source_bucket=images
```

The string config supports all configs described above.

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
2. ✅ version 1.2: make configuration simpler
3. 🔳 version 1.3: file configuration for thumbnails - ability to choose thumbnails file format and some options like
   quality
4. 🔳 version 1.4: make async endpoints
5. 🔳 version 1.5: add DI container 
6. 🔳 version 2.0: refactoring, fixes, code cleanup
