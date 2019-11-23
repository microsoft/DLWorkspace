import unittest
from job_launcher import JobRole


class TestJobRole(unittest.TestCase):

    def test_status_Running(self):
        job_role = JobRole("master", "bd3d090a-53b6-4616-9b6c-fe4a86fd68ea-ps0")

        role_status = job_role.status()
        self.assertEqual("Running", role_status)

    def test_status_NotFound(self):
        job_role = JobRole("master", "bd3d090a-53b6-4616-9b6c-fe4a86fd68ea-ps0-not-found")

        role_status = job_role.status()
        self.assertEqual("NotFound", role_status)

    def test_status_Pending(self):
        # Pod is running, but mark file not existing: JobRole.MARK_POD_READY_FILE
        job_role = JobRole("master", "nginx-cm7kf")

        role_status = job_role.status()
        self.assertEqual("Pending", role_status)

    def test_get_job_roles_dist_job(self):
        job_roles = JobRole.get_job_roles("bd3d090a-53b6-4616-9b6c-fe4a86fd68ea")

        self.assertEqual(3, len(job_roles))

    def test_get_job_roles_regular_job(self):
        job_roles = JobRole.get_job_roles("8ca7fcdf-c4e7-4687-a3fa-1eeea97415c4")

        self.assertEqual(1, len(job_roles))
