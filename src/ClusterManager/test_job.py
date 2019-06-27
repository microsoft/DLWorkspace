import unittest
import json
from job import Job, JobSchema

VALID_JOB_ATTRIBUTES = {
    "jobId": "ce7dca49-28df-450a-a03b-51b9c2ecc69c",
    "userName": "user@foo.com"
}


class TestJobSchema(unittest.TestCase):

    def test_loads(self):
        job_json = json.dumps(VALID_JOB_ATTRIBUTES)

        job, errors = JobSchema().loads(job_json)
        self.assertFalse(errors)
        self.assertEqual(job.job_id, VALID_JOB_ATTRIBUTES["jobId"])
        self.assertEqual(job.email, VALID_JOB_ATTRIBUTES["userName"])

    def test_job_id_schema(self):
        job, errors = JobSchema().load(VALID_JOB_ATTRIBUTES)
        self.assertFalse(errors)

        # uppercase
        attrs = VALID_JOB_ATTRIBUTES.copy()
        attrs.update({"jobId": "First-job"})
        job, errors = JobSchema().load(attrs)
        self.assertTrue("jobId" in errors)

        # space
        attrs = VALID_JOB_ATTRIBUTES.copy()
        attrs.update({"jobId": "first job"})
        job, errors = JobSchema().load(attrs)
        self.assertTrue("jobId" in errors)

    def test_dump(self):
        job = Job(job_id="test-job", email="user@foo.com")

        result, errors = JobSchema().dump(job)

        self.assertFalse(errors)
        self.assertEqual(result["jobId"], "test-job")
        self.assertEqual(result["userName"], "user@foo.com")


class TestJob(unittest.TestCase):

    def create_a_job(self):
        job, errors = JobSchema().load(VALID_JOB_ATTRIBUTES)
        self.assertFalse(errors)
        return job

    def test_add_mountpoints_with_none(self):
        job = self.create_a_job()
        job.add_mountpoints(None)

    def test_add_mountpoints_without_name(self):
        job = self.create_a_job()

        # add one mountpoint without "name"
        mountpoint1 = {
            "enabled": True,
            "containerPath": "/home/username",
            "hostPath": "/dlwsdata/work/username",
        }
        job.add_mountpoints(mountpoint1)
        self.assertEqual(1, len(job.mountpoints))

    def test_add_mountpoints(self):
        job = self.create_a_job()

        # add one mountpoint
        mountpoint1 = {
            "enabled": True,
            "containerPath": "/home/username",
            "hostPath": "/dlwsdata/work/username",
            "name": "homefolder"
        }
        job.add_mountpoints(mountpoint1)
        self.assertEqual(1, len(job.mountpoints))

        # would silently skip
        job.add_mountpoints(mountpoint1)
        self.assertEqual(1, len(job.mountpoints))

        # name would be normalized, only allow alphanumeric, so it would be a duplicate
        mountpoint1a = {
            "enabled": True,
            "containerPath": "/home/path",
            "hostPath": "/dlwsdata/work/path",
            "name": "homefolder-"
        }
        job.add_mountpoints(mountpoint1a)
        self.assertEqual(1, len(job.mountpoints))

        # add another mountpoint
        mountpoint2 = {
            "enabled": True,
            "containerPath": "/home/path1",
            "hostPath": "/dlwsdata/work/path1",
            "name": "homepath1"
        }
        job.add_mountpoints(mountpoint2)
        self.assertEqual(2, len(job.mountpoints))

        # add a list
        mountpoints = [{
            "enabled": True,
            "containerPath": "/home/path2",
            "hostPath": "/dlwsdata/work/path2",
            "name": "homepath2"
        }]
        job.add_mountpoints(mountpoints)
        self.assertEqual(3, len(job.mountpoints))
