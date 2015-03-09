import os
import boto
import datetime


class S3(object):
    def __init__(self, bucket_name, host):
        self.conn = boto.connect_s3(host=host)
        self.bucket_name = bucket_name
        self.bucket = self.conn.get_bucket(bucket_name)

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
        key.set_contents_from_file(file)
        key.set_acl(acl)
