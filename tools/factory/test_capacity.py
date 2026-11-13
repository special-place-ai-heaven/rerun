import unittest
import limits


class Capacity(unittest.TestCase):
    def test_shipped_settings_40_and_2(self):
        self.assertEqual((limits.capacity({}), limits.per_job_cap({})), (3, 2))
        self.assertEqual((limits.capacity(), limits.per_job_cap()), (40, 2))
        self.assertEqual(limits.capacity({"builder_capacity": 5}), 5)
        self.assertEqual(limits.per_job_cap({"per_job_cap": 1}), 1)


if __name__ == "__main__":
    unittest.main()
