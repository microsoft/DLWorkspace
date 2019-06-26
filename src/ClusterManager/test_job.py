import unittest
from job import Job, JobSchema


class TestJobSchema(unittest.TestCase):
    def test_loads(self):
        job_json = '{"jobId": "ce7dca49-28df-450a-a03b-51b9c2ecc69c"}'

        job, errors = JobSchema().loads(job_json)
        self.assertFalse(errors)
        self.assertEqual(job.job_id, "ce7dca49-28df-450a-a03b-51b9c2ecc69c")

        job, _ = JobSchema().load({"jobId": "first_job"})
        self.assertEqual(job.job_id, "first_job")

    def test_job_id_schema(self):
        # regex used for validation is '[a-z]([-a-z0-9]*[a-z0-9])?'
        job, errors = JobSchema().load({"jobId": "8first_job"})
        self.assertEqual(errors, {'jobId': ['String does not match expected pattern.']})

        job, errors = JobSchema().load({"jobId": "8First_job"})
        self.assertEqual(errors, {'jobId': ['String does not match expected pattern.']})

        job, errors = JobSchema().load({"jobId": "first-job"})
        self.assertFalse(errors)

    def test_dump(self):
        job = Job(job_id="test_job")

        result, errors = JobSchema().dump(job)

        self.assertFalse(errors)
        self.assertEqual(result["jobId"], "test_job")


class TestJob(unittest.TestCase):

    def test_add_mountpoints_with_none(self):
        job, errors = JobSchema().load({"jobId": "first_job"})
        self.assertFalse(errors)

        job.add_mountpoints(None)

    def test_add_mountpoints_without_name(self):
        job, errors = JobSchema().load({"jobId": "first_job"})
        self.assertFalse(errors)

        # add one mountpoint without "name"
        mountpoint1 = {
            "enabled": True,
            "containerPath": "/home/username",
            "hostPath": "/dlwsdata/work/username",
        }
        job.add_mountpoints(mountpoint1)
        self.assertEqual(1, len(job.mountpoints))

    def test_add_mountpoints(self):
        job, errors = JobSchema().load({"jobId": "first_job"})
        self.assertFalse(errors)

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

