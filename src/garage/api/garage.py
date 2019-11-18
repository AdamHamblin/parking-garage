from enum import Enum
import os
import json
import logging
import sys

# dir_path = os.path.dirname(os.path.realpath(__file__))
# project_root, tail = os.path.split(dir_path)
# sys.path.insert(0, os.path.abspath(os.path.join(project_root, '..')))

from src.garage.utils import APIError, status_codes

# from context import APIError, status_codes
# from utils import APIError, status_codes

logger = logging.getLogger(__name__)


# Garage is the Parent object. Contains Levels.
class Garage(object):
    def __init__(self, document=None):
        levels = document.get('levels', {})
        self.name = document.get('name', '')
        self.levels = self.set_levels(levels)
        self.vehicle_count = 0
        self.max_capacity = 0
        self.moto_count = 0
        self.car_count = 0
        self.bus_count = 0
        self.available = bool
        self.available_ids = []
        self.assigned_ids = []
        self.available_spot_types = []
        self.available_spots = []
        self.assigned_spots = []
        self._spot_type_map = self.spot_type_map
        self._next_spot_map = self.next_spot_map
        self.initialize_spot_map()
        self.map_status()

    @property
    def spot_type_map(self):
        spot_type_map = {
            Garage.Spot.SpotType.MOTORCYCLE: [Garage.Vehicle.VehicleType.MOTORCYCLE],
            Garage.Spot.SpotType.COMPACT: [Garage.Vehicle.VehicleType.MOTORCYCLE,
                                           Garage.Vehicle.VehicleType.CAR],
            Garage.Spot.SpotType.LARGE: [Garage.Vehicle.VehicleType.MOTORCYCLE,
                                         Garage.Vehicle.VehicleType.CAR,
                                         Garage.Vehicle.VehicleType.BUS]
        }
        return spot_type_map

    # next_spot_map stores the next allocatable space for each vehicle type
    @property
    def next_spot_map(self):
        spot_map = {
            Garage.Vehicle.VehicleType.MOTORCYCLE: Garage.Location,
            Garage.Vehicle.VehicleType.CAR: Garage.Location,
            Garage.Vehicle.VehicleType.BUS: Garage.Location
        }
        return spot_map

    # assign levels from json to objects
    def set_levels(self, levels):
        logger.debug('Setting garage levels')
        new_levels = {}
        for level_id, level in levels.items():
            logger.debug('Creating Level object: ' + level_id)
            new_levels[level_id] = self.Level(level_id, level['rows'])

        return new_levels

    # initialize the next_spot_map
    def initialize_spot_map(self):
        logger.debug('Initializing spot map')
        self.set_next_spot(self.Vehicle.VehicleType.MOTORCYCLE,
                           self.get_spot(self.Vehicle.VehicleType.MOTORCYCLE))
        self.set_next_spot(self.Vehicle.VehicleType.CAR,
                           self.get_spot(self.Vehicle.VehicleType.CAR))
        self.set_next_spot(self.Vehicle.VehicleType.BUS,
                           self.get_spot(self.Vehicle.VehicleType.BUS))

    # sets next spot of one vehicle type of the next_spot_map
    # update availability
    def set_next_spot(self, vehicle_type, location):
        logger.debug('Setting next spot for: ' + self.Vehicle.VehicleType.MOTORCYCLE.name)
        self._next_spot_map[vehicle_type] = location
        if location.spots:
            self.available = True
            if vehicle_type.name not in self.available_spot_types:
                self.available_spot_types.append(vehicle_type.name)
        else:
            if vehicle_type.name in self.available_spot_types:
                logger.debug('Setting full for: ' + self.Vehicle.VehicleType.MOTORCYCLE.name)
                self.available_spot_types.remove(vehicle_type.name)
            if not self.available_spot_types:
                logger.debug('Garage full. Setting available status.')
                self.available = False

    # returns next spot of one vehicle type of the next_spot_map
    def get_next_spot(self, vehicle_type):
        return self._next_spot_map[vehicle_type]

    # get all counts from actual document in case initial counts are incorrect
    def map_status(self):
        # hold found counts
        logger.debug('Initializing status map')
        status_map = {
            'max_capacity': 0,
            'vehicle_count': 0,
            'moto_count': 0,
            'car_count': 0,
            'bus_count': 0,
            'assigned_ids': [],
            'available_ids': [],
            'available_spots': [],
            'assigned_spots': []}
        for level in self.levels:
            logger.debug('Evaluating level ' + level)
            for row in self.levels[level].rows:
                logger.debug('Row ' + row)
                logger.debug('Updating max_capacity count')
                status_map['max_capacity'] += len(self.levels[level].rows[row].spots)
                for spot in self.levels[level].rows[row].spots:
                    vehicle = self.levels[level].rows[row].spots[spot].vehicle
                    if vehicle:
                        logger.debug('Appending assigned spot: ' + spot)
                        status_map['assigned_spots'].append(spot)
                        if vehicle.id not in status_map['assigned_ids']:
                            logger.debug('Appending assigned vehicle: ' + vehicle.id)
                            status_map['assigned_ids'].append(vehicle.id)
                            logger.debug('Incrementing vehicle count')
                            status_map['vehicle_count'] += 1
                            if vehicle.vehicle_type == Garage.Vehicle.VehicleType.MOTORCYCLE:
                                logger.debug('Incrementing vehicle type count: ' + vehicle.vehicle_type.name)
                                status_map['moto_count'] += 1
                            if vehicle.vehicle_type == Garage.Vehicle.VehicleType.CAR:
                                logger.debug('Incrementing vehicle type count: ' + vehicle.vehicle_type.name)
                                status_map['car_count'] += 1
                            if vehicle.vehicle_type == Garage.Vehicle.VehicleType.BUS:
                                logger.debug('Incrementing vehicle type count: ' + vehicle.vehicle_type.name)
                                status_map['bus_count'] += 1
                    else:
                        logger.debug('Appending available spot: ' + spot)
                        status_map['available_spots'].append(spot)
        self.update_status(status_map)

    # update values of garage per status map
    def update_status(self, status_map):
        logger.debug('Creating list of available vehicle ids')
        new_ids = self.create_vehicle_ids(status_map['max_capacity'])
        status_map['available_ids'] = self.remove_assigned_ids(new_ids, status_map['assigned_ids'])

        logger.debug('Updating max_capacity')
        self.max_capacity = status_map['max_capacity']

        logger.debug('Updating vehicle_count')
        self.vehicle_count = status_map['vehicle_count']

        logger.debug('Updating moto_count')
        self.moto_count = status_map['moto_count']

        logger.debug('Updating car_count')
        self.car_count = status_map['car_count']

        logger.debug('Updating bus_count')
        self.bus_count = status_map['bus_count']

        # update available ids. This is safe because found assigned ids have been removed from available list,
        # therefore they cannot assigned to another vehicle
        logger.debug('Updating available ids')
        self.available_ids = self.sort_ids(status_map['available_ids'])

        logger.debug('Updating assigned_ids')
        self.assigned_ids = self.sort_ids(status_map['assigned_ids'])

        logger.debug('Updating available_spots')
        self.available_spots = self.sort_ids(status_map['available_spots'])

        logger.debug('Updating assigned_spots')
        self.assigned_spots = self.sort_ids(status_map['assigned_spots'])

    # returns first available vehicle id
    # removes id from available ids and adds to assigned ids
    def get_vehicle_id(self):
        logger.debug('Getting first available vehicle id')
        veh_id = self.available_ids[0]
        logger.debug('Updating available vehicle ids')
        updated_available = self.available_ids
        updated_available.remove(veh_id)
        self.available_ids = self.sort_ids(updated_available)
        logger.debug('Updating assigned vehicle ids')
        updated_assigned = self.assigned_ids
        updated_assigned.append(veh_id)
        self.assigned_ids = self.sort_ids(updated_assigned)
        if not self.available_ids:
            logger.debug('No available vehicle ids. Updating available status.')
            self.available = False
        return veh_id

    # returns vehicle id from assigned ids to the vehicle ids list
    def unassign_vehicle_id(self, vehicle):
        logger.debug('Unassigning vehicle id')
        if vehicle.id in self.assigned_ids:
            logger.debug('Updating assigned vehicle ids')
            updated_assigned = self.assigned_ids
            updated_assigned.remove(vehicle.id)
            self.assigned_ids = self.sort_ids(updated_assigned)
            logger.debug('Updating available vehicle ids')
            updated_available = self.available_ids
            updated_available.append(vehicle.id)
            self.available_ids = self.sort_ids(updated_available)
        else:
            logger.debug('Vehicle ID was not assigned')
            raise APIError(code='Invalid Vehicle ID',
                           cause='Invalid Vehicle ID',
                           message='Vehicle ID was not assigned in system',
                           status=status_codes.HTTP_NOT_FOUND)

    # create new vehicle object
    def set_vehicle(self, vehicle_type):
        logger.debug('Generating new Vehicle object')
        new_vehicle = Garage.Vehicle(self.get_vehicle_id(), vehicle_type)
        return new_vehicle

    # increment overall vehicle count and vehicle type count
    def increment_vehicle_count(self, vehicle):
        logger.debug('Incrementing vehicle count')
        self.vehicle_count += 1
        if vehicle.vehicle_type == Garage.Vehicle.VehicleType.MOTORCYCLE:
            logger.debug('Incrementing vehicle type count: ' + vehicle.vehicle_type.name)
            self.moto_count += 1
        if vehicle.vehicle_type == Garage.Vehicle.VehicleType.CAR:
            logger.debug('Incrementing vehicle type count: ' + vehicle.vehicle_type.name)
            self.car_count += 1
        if vehicle.vehicle_type == Garage.Vehicle.VehicleType.BUS:
            logger.debug('Incrementing vehicle type count: ' + vehicle.vehicle_type.name)
            self.bus_count += 1

    # increment overall vehicle count and vehicle type count
    def decrement_vehicle_count(self, vehicle):
        logger.debug('Decrementing vehicle count')
        self.vehicle_count -= 1
        if vehicle.vehicle_type == Garage.Vehicle.VehicleType.MOTORCYCLE:
            logger.debug('Decrementing vehicle type count: ' + vehicle.vehicle_type.name)
            self.moto_count -= 1
        if vehicle.vehicle_type == Garage.Vehicle.VehicleType.CAR:
            logger.debug('Decrementing vehicle type count: ' + vehicle.vehicle_type.name)
            self.car_count -= 1
        if vehicle.vehicle_type == Garage.Vehicle.VehicleType.BUS:
            logger.debug('Decrementing vehicle type count: ' + vehicle.vehicle_type.name)
            self.bus_count -= 1

    # find allocatable spot(s) in garage for vehicle type and return with level and row
    # as Location object
    def get_spot(self, vehicle_type=None):
        logger.debug('Getting required number of spots')
        spots_required = 1
        if vehicle_type == Garage.Vehicle.VehicleType.BUS:
            spots_required = 5
        logger.debug('Getting location with required spots')
        location = Garage.Location()
        for level in self.levels:
            for row in self.levels[level].rows:
                spots_found = []
                for spot in self.levels[level].rows[row].spots:
                    spot_type = self.levels[level].rows[row].spots[spot].spot_type
                    if vehicle_type in self._spot_type_map[spot_type]:
                        if not self.levels[level].rows[row].spots[spot].vehicle:
                            spot = self.levels[level].rows[row].spots[spot]
                            spots_found.append(spot)
                        if len(spots_found) == spots_required:
                            location.level = self.levels[level]
                            location.row = self.levels[level].rows[row]
                            location.spots = spots_found
                            logger.debug('Location found')
                            return location
        logger.debug('No location found. Returning empty location')
        return location

    # assign vehicle to a spot
    def assign_spot(self, location, vehicle):
        level = location.level
        row = location.row
        spots = location.spots
        for spot in spots:
            logger.debug('Assigning vehicle ' + vehicle.id +
                         ' to spot: ' + spot.id)
            self.levels[level.id].rows[row.id].spots[spot.id].vehicle = vehicle
            self.assign_spot_id(spot)
        self.increment_vehicle_count(vehicle)
        next_location = self.get_spot(vehicle.vehicle_type)
        self.set_next_spot(vehicle.vehicle_type, next_location)

    # returns spot id from available spots to the assigned spots
    def assign_spot_id(self, spot):
        if spot.id in self.available_spots:
            logger.debug('Updating available spots')
            updated_available = self.available_spots
            updated_available.remove(spot.id)
            self.available_spots = self.sort_ids(updated_available)
            logger.debug('Updating assigned spots')
            updated_assigned = self.assigned_spots
            updated_assigned.append(spot.id)
            self.assigned_spots = self.sort_ids(updated_assigned)

    # check vehicle assignment of a spot
    def check_spot(self, location):
        level = location.level
        row = location.row
        spots = location.spots
        vehicle_in_spot = None
        for spot in spots:
            logger.debug('Checking spot: ' + spot.id)
            vehicle_in_spot = self.levels[level.id].rows[row.id].spots[spot.id].vehicle
        return vehicle_in_spot

    # unassign vehicle to a spot
    def unassign_spot(self, location, vehicle):
        level = location.level
        row = location.row
        spots = location.spots
        for spot in spots:
            logger.debug('Unassigning vehicle ' + vehicle.id +
                         ' from spot: ' + spot.id)
            self.levels[level.id].rows[row.id].spots[spot.id].vehicle = None
            self.unassign_spot_id(spot)
        self.unassign_vehicle_id(vehicle)
        self.decrement_vehicle_count(vehicle)
        next_location = self.get_spot(vehicle.vehicle_type)
        self.set_next_spot(vehicle.vehicle_type, next_location)

    # returns spot id from assigned spots to the available spots
    def unassign_spot_id(self, spot):
        if spot.id in self.assigned_spots:
            logger.debug('Updating assigned spots')
            updated_assigned = self.assigned_spots
            updated_assigned.remove(spot.id)
            self.assigned_spots = self.sort_ids(updated_assigned)
            logger.debug('Updating available spots')
            updated_available = self.available_spots
            updated_available.append(spot.id)
            self.available_spots = self.sort_ids(updated_available)

    # Level objects are contained by Garage. Level contains Rows.
    class Level:
        def __init__(self, level_id, rows):
            self.id = level_id
            self.rows = self.set_rows(rows)

        # assign rows from json to objects
        @staticmethod
        def set_rows(rows):
            new_rows = {}
            for row_id, row in rows.items():
                logger.debug('Creating Row object: ' + row_id)
                new_rows[row_id] = Garage.Row(row_id, row['spots'])

            return new_rows

    # Row objects are contained by Level. Row contains Spots.
    class Row:
        def __init__(self, row_id, spots):
            self.id = row_id
            self.spots = self.set_spots(spots)

        # assign spots from json to objects
        @staticmethod
        def set_spots(spots):
            new_spots = {}
            for spot_id, spot in spots.items():
                logger.debug('Creating Spot object: ' + spot_id)
                spot_type = spot['spot_type']
                vehicle = spot['vehicle']
                new_spots[spot_id] = Garage.Spot(spot_id, spot_type, vehicle)

            return new_spots

    # Spot objects are contained by Rows. Spots can contain Vehicle.
    class Spot:
        def __init__(self, spot_id, spot_type, vehicle=None):
            self.id = spot_id
            self.spot_type = self.SpotType(spot_type)
            self.vehicle = None

            if vehicle:
                self.vehicle = self.set_vehicle(vehicle)

        # SpotType Enum for easy assignment of SpotType to Spot
        class SpotType(Enum):
            MOTORCYCLE = 0
            COMPACT = 1
            LARGE = 2

        # assign Vehicle in spot in doc to Vehicle object
        @staticmethod
        def set_vehicle(vehicle):
            logger.debug('Creating Vehicle object: ' + vehicle['vehicle_id'] +
                         ' of type: ' + str(vehicle['vehicle_type']))
            new_vehicle = Garage.Vehicle(vehicle['vehicle_id'], vehicle['vehicle_type'])
            return new_vehicle

    # Vehicle objects are assigned to Spots
    class Vehicle:
        def __init__(self, vehicle_id, vehicle_type):
            self.id = str(vehicle_id)
            self.vehicle_type = self.VehicleType(vehicle_type)

        # VehicleType Enum for easy assignment of VehicleType to Vehicle
        class VehicleType(Enum):
            MOTORCYCLE = 0
            CAR = 1
            BUS = 2

    # Location serves as a container to make assignment of vehicles to spots
    # more efficient
    class Location:
        def __init__(self, level=None, row=None, spots=None):
            self.level = None
            self.row = None
            self.spots = None
            if isinstance(level, Garage.Level):
                self.level = level
            if isinstance(row, Garage.Row):
                self.row = row
            if isinstance(spots, list):
                new_spots = []
                for spot in spots:
                    if isinstance(spot, Garage.Spot):
                        new_spots.append(spot)
                if new_spots:
                    self.spots = new_spots

    # this method insures numeric order of list of ids
    @staticmethod
    def sort_ids(ids):
        logger.debug('Sorting ids as ints.')
        int_ids = list(map(int, ids))
        int_ids = sorted(int_ids)
        str_ids = list(map(str, int_ids))
        return str_ids

    # returns list of all ids based on capacity of garage
    @staticmethod
    def create_vehicle_ids(max_capacity):
        logger.debug('Creating ranged list of vehicle ids')
        int_ids = sorted(list(range(0, max_capacity)))
        str_ids = list(map(str, int_ids))
        return str_ids

    # returns list of available ids with assigned ids removed.
    @staticmethod
    def remove_assigned_ids(available_ids, assigned_ids):
        logger.debug('Removing assigned list from available list')
        available_ids = list(set(available_ids) - set(assigned_ids))
        return available_ids

    @staticmethod
    def decouple_spot_id(spots):
        if '-' in spots:
            logger.debug('Decoupling hyphenated bus spot: ' + str(spots))
            first, last = list(map(int, spots.split('-')))
            spots = list(map(str, range(first, last + 1)))
        else:
            logger.debug('Making single spot iterable')
            spots = [spots]
        return spots

    @staticmethod
    def format_spot(spots):
        logger.debug('Formating spot id for output')
        spot_id = spots[0].id
        last_spot_id = spots[len(spots) - 1].id
        if last_spot_id != spot_id:
            spot_id = spot_id + '-' + last_spot_id
        spot_type = spots[0].spot_type.name
        return {'spot_id': spot_id, 'spot_type': spot_type}

    # parse garage object to dictionary
    def garage_to_dict(self):
        logger.debug('Parsing Garage object to dict')
        garage = self.__dict__
        for level_id in garage['levels']:
            logger.debug('Parsing Level object to dict: ' + level_id)
            level = garage['levels'][level_id].__dict__
            del level['id']
            for row_id in level['rows']:
                logger.debug('Parsing Row object to dict: ' + row_id)
                row = level['rows'][row_id].__dict__
                del row['id']
                for spot_id in row['spots']:
                    logger.debug('Parsing Spot object to dict: ' + spot_id)
                    spot = row['spots'][spot_id].__dict__
                    del spot['id']
                    spot['spot_type'] = spot['spot_type'].__dict__.get('_value_', '0')  # should be int
                    if spot['vehicle']:
                        logger.debug('Parsing Vehicle object to dict')
                        vehicle = spot['vehicle'].__dict__
                        if 'id' in vehicle:
                            vehicle['vehicle_id'] = vehicle.pop('id')
                        if not isinstance(vehicle['vehicle_type'], int):
                            vehicle['vehicle_type'] = vehicle['vehicle_type'].value
                    else:
                        vehicle = {}
                    spot['vehicle'] = vehicle
                    row['spots'][spot_id] = spot
                level['rows'][row_id] = row
            garage['levels'][level_id] = level
        logger.debug('Deleting unneeded fields from garage dict')
        del garage['_spot_type_map']
        del garage['_next_spot_map']
        del garage['vehicle_count']
        del garage['max_capacity']
        del garage['moto_count']
        del garage['car_count']
        del garage['bus_count']
        del garage['available']
        del garage['available_ids']
        del garage['assigned_ids']
        del garage['available_spots']
        del garage['available_spot_types']
        del garage['assigned_spots']

        return garage


def build_garage_doc(fn=None):
    fqn = get_file_path(fn)
    with open(fqn, 'r') as json_file:
        doc_data = json.load(json_file)

    return doc_data


def write_garage_doc(fn=None, data=None):
    fqn = get_file_path(fn)
    parsed_dict = data.garage_to_dict()
    with open(fqn, 'w') as json_file:
        json.dump(parsed_dict, json_file, indent=2)


def get_file_path(fn=None):
    if not fn:
        fn = 'main_garage_v1.json'

    logger.debug('Locating file path')
    dir_path = os.path.dirname(os.path.realpath(__file__))
    head, tail = os.path.split(dir_path)
    src, tail = os.path.split(head)
    project_root, tail = os.path.split(src)

    return os.path.join(project_root, 'data', fn)
