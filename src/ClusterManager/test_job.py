import unittest
import json
import sys
import os
from job import Job, JobSchema

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))
from config import config


VALID_JOB_ATTRIBUTES = {
    "cluster": config,
    "jobId": "ce7dca49-28df-450a-a03b-51b9c2ecc69c",
    "userName": "user@foo.com",
    "jobPath": "user_alias/jobs/date/job_id",
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
        job = Job(
            cluster=config,
            job_id="test-job",
            email="user@foo.com"
        )

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

    def test_get_homefolder_hostpath(self):
        job = self.create_a_job()
        self.assertEqual("/dlwsdata/work/user", job.get_homefolder_hostpath())

    def test_get_hostpath(self):
        job = self.create_a_job()
        self.assertEqual("user_alias/jobs/date/job_id", job.job_path)
        self.assertEqual("/dlwsdata/work/user_alias/jobs/date/job_id", job.get_hostpath(job.job_path))

    def test_job_work_data_mountpoints(self):
        job = self.create_a_job()

        job.job_path = "user_alias/jobs/date/job_id"
        job.work_path = "user_alias"
        job.data_path = ""

        self.assertEqual("/dlwsdata/work/user_alias/jobs/date/job_id", job.job_path_mountpoint()["hostPath"])
        self.assertEqual("/dlwsdata/work/user_alias", job.work_path_mountpoint()["hostPath"])
        self.assertEqual("/dlwsdata/storage/", job.data_path_mountpoint()["hostPath"])

        job.add_mountpoints(job.job_path_mountpoint())
        job.add_mountpoints(job.work_path_mountpoint())
        job.add_mountpoints(job.data_path_mountpoint())
        self.assertEquals(3, len(job.mountpoints))

    def test_get_template(self):
        job = self.create_a_job()

        self.assertIsNotNone(job.get_template())

    def test_is_custom_scheduler_enabled(self):
        job = self.create_a_job()

        self.assertFalse(job.is_custom_scheduler_enabled())

        # TODO !!! notice, it would change all the 'cluster' settings
        job.cluster["kube_custom_scheduler"] = True
        self.assertTrue(job.is_custom_scheduler_enabled())

    def test_get_rest_api_url(self):
        job = self.create_a_job()

        self.assertEqual("http://faked.uri/", job.get_rest_api_url())

    def test_get_rack(self):
        job = self.create_a_job()

        self.assertEqual(None, job.get_rack())
