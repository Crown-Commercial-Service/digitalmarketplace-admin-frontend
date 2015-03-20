import os
import boto
import datetime
import mimetypes


class S3(object):
    def __init__(self, bucket_name=None, host='s3-eu-west-1.amazonaws.com'):
        conn = boto.connect_s3(host=host)

        self.bucket_name = bucket_name
        self.bucket = conn.get_bucket(bucket_name)

    def save(self, path, name, file, acl='public-read'):
        timestamp = datetime.datetime.utcnow().isoformat()

        full_path = os.path.join(path, name)

        if self.bucket.get_key(full_path):
            self.bucket.copy_key(
                os.path.join(path, '{}-{}'.format(timestamp, name)),
                self.bucket_name,
                full_path
            )

        key = self.bucket.new_key(full_path)
        mimetype, _ = mimetypes.guess_type(key.name)
        key.set_contents_from_file(file, headers={'Content-Type': mimetype})
        key.set_acl(acl)
