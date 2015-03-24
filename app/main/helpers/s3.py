import os
import boto
import datetime
import mimetypes


class S3(object):
    def __init__(self, bucket_name=None, host='s3-eu-west-1.amazonaws.com'):
        conn = boto.connect_s3(host=host)

        self.bucket_name = bucket_name
        self.bucket = conn.get_bucket(bucket_name)

    def save(self, path, file, existing_path=None, acl='public-read'):
        path = path.lstrip('/')

        if existing_path:
            existing_path = existing_path.lstrip('/')
            self._move_existing(existing_path)
        else:
            self._move_existing(path)

        key = self.bucket.new_key(path)
        key.set_contents_from_file(file,
                                   headers={'Content-Type':
                                            self._get_mimetype(key.name)})
        key.set_acl(acl)
        return key

    def _move_existing(self, existing_path):
        timestamp = datetime.datetime.utcnow().isoformat()

        if self.bucket.get_key(existing_path):
            path, name = os.path.split(existing_path)
            self.bucket.copy_key(
                os.path.join(path, '{}-{}'.format(timestamp, name)),
                self.bucket_name,
                existing_path
            )

            self.bucket.delete_key(existing_path)

    def _get_mimetype(self, filename):
        mimetype, _ = mimetypes.guess_type(filename)
        return mimetype
