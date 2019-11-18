import os
import sys
import unittest

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(dir_path, '..')))

from tests.context import (build_garage_doc,
                           Garage,
                           http_put,
                           http_delete,
                           APIError,
                           status_codes,
                           Request,
                           Response)


def get_garage_data(fn='main_garage_v1.json'):
    return build_garage_doc(fn=fn)


class TestGarageParking(unittest.TestCase):
    def setUp(self):
        self.req = Request()
        self.resp = Response()
        self.params = ''

    def test_park_motorcycle(self):
        # vehicle type 0 is motorcycle
        self.req.body = {'vehicle_type': 0}

        # ---------- call method ----------
        # get original document
        original = get_garage_data()

        http_put(self.req, self.resp, self.params)

        # get updated document
        updated = get_garage_data()

        # ---------- evaluate response ----------
        # assert response body
        self.assertIn('vehicle_id', self.resp.body)
        self.assertIn('vehicle_type', self.resp.body)
        self.assertIn('level', self.resp.body)
        self.assertIn('row', self.resp.body)
        self.assertIn('spot_id', self.resp.body)
        self.assertIn('spot_type', self.resp.body)
        self.assertEqual('MOTORCYCLE', self.resp.body['vehicle_type'])

        # assert response status
        self.assertEqual(self.resp.status, status_codes.HTTP_CREATED)

        # assert document has changed
        self.assertNotEqual(original, updated)

        # assert 1 spots occupied
        spots = Garage.decouple_spot_id(self.resp.body['spot_id'])
        self.assertEqual(len(spots), 1)

        for spot in spots:
            # assert spot was empty in original
            original_location = \
                original['levels'][self.resp.body['level']]['rows'][self.resp.body['row']]['spots'][spot]
            self.assertEqual({}, original_location['vehicle'])

            # assert vehicle is in location
            updated_location = \
                updated['levels'][self.resp.body['level']]['rows'][self.resp.body['row']]['spots'][spot]
            self.assertEqual(self.resp.body['vehicle_id'], updated_location['vehicle']['vehicle_id'])
            self.assertEqual(self.req.body['vehicle_type'], updated_location['vehicle']['vehicle_type'])

            # assert location is permissible for vehicle type
            self.assertIn(updated_location['spot_type'], [0, 1, 2])

    def test_park_car(self):
        # vehicle type 1 is car
        self.req.body = {'vehicle_type': 1}

        # ---------- call method ----------

        # get original
        original = get_garage_data()

        http_put(self.req, self.resp, self.params)

        # get updated document
        updated = get_garage_data()

        # ---------- evaluate response ----------
        # assert response body
        self.assertIn('vehicle_id', self.resp.body)
        self.assertIn('vehicle_type', self.resp.body)
        self.assertIn('level', self.resp.body)
        self.assertIn('row', self.resp.body)
        self.assertIn('spot_id', self.resp.body)
        self.assertIn('spot_type', self.resp.body)
        self.assertEqual('CAR', self.resp.body['vehicle_type'])

        # assert response status
        self.assertEqual(self.resp.status, status_codes.HTTP_CREATED)

        # assert document has changed
        self.assertNotEqual(original, updated)

        # assert 1 spots occupied
        spots = Garage.decouple_spot_id(self.resp.body['spot_id'])
        self.assertEqual(len(spots), 1)

        for spot in spots:
            # assert spot was empty in original
            original_location = \
                original['levels'][self.resp.body['level']]['rows'][self.resp.body['row']]['spots'][spot]
            self.assertEqual({}, original_location['vehicle'])

            # assert vehicle is in location
            updated_location = \
                updated['levels'][self.resp.body['level']]['rows'][self.resp.body['row']]['spots'][spot]
            self.assertEqual(self.resp.body['vehicle_id'], updated_location['vehicle']['vehicle_id'])
            self.assertEqual(self.req.body['vehicle_type'], updated_location['vehicle']['vehicle_type'])

            # assert location is permissible for vehicle type
            self.assertIn(updated_location['spot_type'], [1, 2])

    def test_park_bus(self):
        # vehicle type 2 is bus
        self.req.body = {'vehicle_type': 2}

        # ---------- call method ----------
        # get original
        original = get_garage_data()

        http_put(self.req, self.resp, self.params)

        # get updated document
        updated = get_garage_data()

        # ---------- evaluate response ----------
        # assert response body
        self.assertIn('vehicle_id', self.resp.body)
        self.assertIn('vehicle_type', self.resp.body)
        self.assertIn('level', self.resp.body)
        self.assertIn('row', self.resp.body)
        self.assertIn('spot_id', self.resp.body)
        self.assertIn('spot_type', self.resp.body)
        self.assertEqual('BUS', self.resp.body['vehicle_type'])

        # assert response status
        self.assertEqual(self.resp.status, status_codes.HTTP_CREATED)

        # assert document has changed
        self.assertNotEqual(original, updated)

        # assert 5 spots occupied
        spots = Garage.decouple_spot_id(self.resp.body['spot_id'])
        self.assertEqual(len(spots), 5)

        last_spot = int(spots[0]) - 1
        for spot in spots:
            # assert spot is consecutive
            self.assertEqual(int(spot), last_spot + 1)
            last_spot = int(spot)

            # assert spot was empty in original
            original_location = \
                original['levels'][self.resp.body['level']]['rows'][self.resp.body['row']]['spots'][spot]
            self.assertEqual({}, original_location['vehicle'])

            # assert vehicle is in location
            updated_location = \
                updated['levels'][self.resp.body['level']]['rows'][self.resp.body['row']]['spots'][spot]
            self.assertEqual(self.resp.body['vehicle_id'], updated_location['vehicle']['vehicle_id'])
            self.assertEqual(self.req.body['vehicle_type'], updated_location['vehicle']['vehicle_type'])

            # assert location is permissible for vehicle type
            self.assertEqual(updated_location['spot_type'], 2)

    def test_exit_garage_moto(self):
        self.req.body = {'vehicle_id': '0',
                         'spot_id': '0',
                         'row': '0',
                         'level': '0'}

        # ---------- call method ----------
        # get original
        original = get_garage_data()

        http_delete(self.req, self.resp, self.params)

        # get updated document
        updated = get_garage_data()

        # ---------- evaluate response ----------
        # assert response status
        self.assertEqual(self.resp.status, status_codes.HTTP_OK)

        # assert document has changed
        self.assertNotEqual(original, updated)

        spots = Garage.decouple_spot_id(self.req.body['spot_id'])

        for spot in spots:
            # assert vehicle was in original location
            original_location = \
                original['levels'][self.req.body['level']]['rows'][self.req.body['row']]['spots'][spot]
            self.assertEqual(self.req.body['vehicle_id'], original_location['vehicle']['vehicle_id'])

            # assert spot is empty in updated
            updated_location = \
                updated['levels'][self.req.body['level']]['rows'][self.req.body['row']]['spots'][spot]
            self.assertEqual({}, updated_location['vehicle'])

    def test_exit_garage_car(self):
        self.req.body = {'vehicle_id': '1',
                         'spot_id': '2',
                         'row': '0',
                         'level': '0'}

        # ---------- call method ----------
        # get original
        original = get_garage_data()

        http_delete(self.req, self.resp, self.params)

        # get updated document
        updated = get_garage_data()

        # ---------- evaluate response ----------
        # assert response status
        self.assertEqual(self.resp.status, status_codes.HTTP_OK)

        # assert document has changed
        self.assertNotEqual(original, updated)

        spots = Garage.decouple_spot_id(self.req.body['spot_id'])

        for spot in spots:
            # assert vehicle was in original location
            original_location = \
                original['levels'][self.req.body['level']]['rows'][self.req.body['row']]['spots'][spot]
            self.assertEqual(self.req.body['vehicle_id'], original_location['vehicle']['vehicle_id'])

            # assert spot is empty in updated
            updated_location = \
                updated['levels'][self.req.body['level']]['rows'][self.req.body['row']]['spots'][spot]
            self.assertEqual({}, updated_location['vehicle'])

    def test_exit_garage_bus(self):
        self.req.body = {'vehicle_id': '2',
                         'spot_id': '7-11',
                         'row': '0',
                         'level': '0'}

        # ---------- call method ----------
        # get original
        original = get_garage_data()

        http_delete(self.req, self.resp, self.params)

        # get updated document
        updated = get_garage_data()

        # ---------- evaluate response ----------
        # assert response status
        self.assertEqual(self.resp.status, status_codes.HTTP_OK)

        # assert document has changed
        self.assertNotEqual(original, updated)

        spots = Garage.decouple_spot_id(self.req.body['spot_id'])

        for spot in spots:
            # assert vehicle was in original location
            original_location = \
                original['levels'][self.req.body['level']]['rows'][self.req.body['row']]['spots'][spot]
            self.assertEqual(self.req.body['vehicle_id'], original_location['vehicle']['vehicle_id'])

            # assert spot is empty in updated
            updated_location = \
                updated['levels'][self.req.body['level']]['rows'][self.req.body['row']]['spots'][spot]
            self.assertEqual({}, updated_location['vehicle'])


class TestGarageParkingFailures(unittest.TestCase):
    def setUp(self):
        self.req = Request()
        self.resp = Response()
        self.params = ''

    ####################
    #   POST Failures  #
    ####################
    def test_park_invalid_vehicle_type(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_type': 'invalid'}

        # get not_updated
        not_updated = get_garage_data()

        with self.assertRaises(APIError) as context:
            http_put(self.req, self.resp, self.params)

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Input: vehicle_type')
        self.assertEqual(original, not_updated)

    def test_park_bus_full(self):
        garage_doc = get_garage_data(fn='full_garage_bus_v1.json')

        # ---------- call method ----------
        # vehicle type 1 is car
        self.req.body = {'vehicle_type': 2}
        with self.assertRaises(APIError) as context:
            http_put(self.req, self.resp, self.params, document=garage_doc)

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Full for Vehicle Type: BUS')

    def test_park_garage_full(self):
        garage_doc = get_garage_data(fn='full_garage_v1.json')

        # ---------- call method ----------
        # vehicle type 1 is car
        self.req.body = {'vehicle_type': 1}
        with self.assertRaises(APIError) as context:
            http_put(self.req, self.resp, self.params, document=garage_doc)

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Garage Full')

    ####################
    #   PUT Failures   #
    ####################
    def test_exit_invalid_vehicle_id(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_id': 123,
                         'spot_id': '2',
                         'row': '0',
                         'level': '0'}

        with self.assertRaises(APIError) as context:
            http_delete(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Input: vehicle_id')
        self.assertEqual(original, not_updated)

    def test_exit_vehicle_not_found(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_id': 'not a vehicle',
                         'spot_id': '2',
                         'row': '0',
                         'level': '0'}

        with self.assertRaises(APIError) as context:
            http_delete(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Vehicle ID')
        self.assertEqual(original, not_updated)

    def test_exit_invalid_spot_id(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_id': '1',
                         'spot_id': 123,
                         'row': '0',
                         'level': '0'}

        with self.assertRaises(APIError) as context:
            http_delete(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Input: spot_id')
        self.assertEqual(original, not_updated)

    def test_exit_spot_not_found(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_id': '1',
                         'spot_id': 'not a spot',
                         'row': '0',
                         'level': '0'}

        with self.assertRaises(APIError) as context:
            http_delete(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Spot ID')
        self.assertEqual(original, not_updated)

    def test_exit_invalid_row(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_id': '1',
                         'spot_id': '2',
                         'row': 123,
                         'level': '0'}

        with self.assertRaises(APIError) as context:
            http_delete(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Input: row')
        self.assertEqual(original, not_updated)

    def test_exit_row_not_found(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_id': '1',
                         'spot_id': '2',
                         'row': 'not a row',
                         'level': '0'}

        with self.assertRaises(APIError) as context:
            http_delete(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Row ID')
        self.assertEqual(original, not_updated)

    def test_exit_invalid_level(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_id': '1',
                         'spot_id': '2',
                         'row': '0',
                         'level': 123}

        with self.assertRaises(APIError) as context:
            http_delete(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Input: level')
        self.assertEqual(original, not_updated)

    def test_exit_level_not_found(self):
        # get original
        original = get_garage_data()

        # ---------- call method ----------
        self.req.body = {'vehicle_id': '1',
                         'spot_id': '2',
                         'row': '0',
                         'level': 'not a level'}

        with self.assertRaises(APIError) as context:
            http_delete(self.req, self.resp, self.params)

        # get not_updated
        not_updated = get_garage_data()

        # ---------- evaluate response ----------
        self.assertEqual(context.exception.code, 'Invalid Level ID')
        self.assertEqual(original, not_updated)


if __name__ == '__main__':
    unittest.main()
