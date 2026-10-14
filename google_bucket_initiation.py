import os
from google.cloud import storage


class GoogleBucketStorage:

    bucket_connection_object = None
    storage_client = None

    @classmethod
    def initiate_google_bucket_connection(cls):
        cls.storage_client = storage.Client(
            project=os.getenv("PROJECT_ID")
        )
        cls.bucket_connection_object = cls.storage_client.bucket(
            os.getenv("GCS_BUCKET_NAME")
        )

        return cls.bucket_connection_object