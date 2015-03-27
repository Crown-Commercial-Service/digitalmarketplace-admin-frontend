import os
import boto
import boto.exception
import datetime
import mimetypes

from boto.exception import S3ResponseError  # noqa


class S3(object):
    def __init__(self, bucket_name=None, host='s3-eu-west-1.amazonaws.com'):
        conn = boto.connect_s3(host=host)

        self.bucket_name = bucket_name
        self.bucket = conn.get_bucket(bucket_name)

    def save(self, path, file, acl='public-read', move_prefix=None):
        path = path.lstrip('/')

        self._move_existing(path, move_prefix)

        key = self.bucket.new_key(path)
        key.set_contents_from_file(file,
                                   headers={'Content-Type':
                                            self._get_mimetype(key.name)})
        key.set_acl(acl)
        return key

    def _move_existing(self, existing_path, move_prefix=None):
        if move_prefix is None:
            move_prefix = default_move_prefix()

        if self.bucket.get_key(existing_path):
            path, name = os.path.split(existing_path)
            self.bucket.copy_key(
                os.path.join(path, '{}-{}'.format(move_prefix, name)),
                self.bucket_name,
                existing_path
            )

    def _get_mimetype(self, filename):
        mimetype, _ = mimetypes.guess_type(filename)
        return mimetype


def default_move_prefix():
    return datetime.datetime.utcnow().isoformat()
