import unittest

import packet


class RetryPacket(unittest.TestCase):
    def test_retry_has_tail_under_cap(self):
        base = "Chunk A1\nDo the thing.\n"
        fail = "\n".join("line %d" % i for i in range(2000))
        out = packet.retry_packet(base, fail)
        self.assertLessEqual(len(out.encode()), packet.PACKET_CAP)
        self.assertTrue(out.startswith(base))
        self.assertTrue(out.rstrip().endswith("line 1999"))
        self.assertNotIn("line 0\n", out)

    def test_short_failure_kept_whole(self):
        out = packet.retry_packet("base\n", "boom")
        self.assertIn("boom", out)
        self.assertLessEqual(len(out.encode()), packet.PACKET_CAP)

    def test_base_alone_over_cap_is_cut(self):
        out = packet.retry_packet("x" * 9000, "boom", cap=100)
        self.assertLessEqual(len(out.encode()), 100)

    def test_multibyte_tail_stays_valid(self):
        out = packet.retry_packet("b\n", "é" * 5000, cap=300)
        self.assertLessEqual(len(out.encode()), 300)


if __name__ == "__main__":
    unittest.main()
