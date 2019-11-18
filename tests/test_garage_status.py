import os
import sys
import unittest

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(dir_path, '..')))

from tests.context import (build_garage_doc,
                           http_get,
                           status_codes,
                           Request,
                           Response)


def get_garage_data(fn='main_garage_v1.json'):
    return build_garage_doc(fn=fn)


class TestGarageStatus(unittest.TestCase):
    def setUp(self):
        self.req = Request()
        self.resp = Response()
        self.params = ''

    def test_get_status(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        http_get(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        # assert response body
        self.assertIn('name', self.resp.body),
        self.assertIn('max_capacity', self.resp.body),
        self.assertIn('occupancy', self.resp.body),
        self.assertIn('cars', self.resp.body),
        self.assertIn('motorcycles', self.resp.body),
        self.assertIn('buses', self.resp.body),
        self.assertIn('available', self.resp.body),
        self.assertIn('available_spot_types', self.resp.body),
        self.assertIn('available_spots_total', self.resp.body),
        self.assertIn('available_spots', self.resp.body),
        self.assertIn('assigned_spots', self.resp.body),
        self.assertIn('next_car_spot', self.resp.body),
        self.assertIn('next_moto_spot', self.resp.body),
        self.assertIn('next_bus_spot', self.resp.body)

        # assert response status
        self.assertEqual(self.resp.status, status_codes.HTTP_OK)

        # assert document did not change
        self.assertEqual(original, not_updated)


class TestParkingGarageParkVehicleFailures(unittest.TestCase):
    # no relevant failure tests
    pass


if __name__ == '__main__':
    unittest.main()
