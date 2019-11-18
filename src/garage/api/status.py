import logging

from src.garage import utils
from src.garage.api.garage import (Garage,
                                   build_garage_doc,
                                   write_garage_doc)

logger = logging.getLogger(__name__)


# create instance of Garage object from json file
def get_garage_data(fn='main_garage_v1.json'):
    return build_garage_doc(fn=fn)


def update_garage_data(garage, fn='main_garage_v1.json'):
    return write_garage_doc(fn, garage)


def http_get(request, response, params, document=None):
    """ Resource = garage/v1/status """

    if not document:
        logger.debug('Loading garage document')
        document = get_garage_data()

    # create instance of Garage object from json file
    logger.debug('Instantiating Garage class object')
    garage = Garage(document)

    available = str(garage.available)
    available_spot_types = utils.list_of_strings(garage.available_spot_types)
    available_spots_total = len(garage.available_spots)
    available_spots = utils.list_of_strings(garage.available_spots)
    assigned_spots = utils.list_of_strings(garage.assigned_ids)
    next_car_spot = str(garage.get_next_spot(garage.Vehicle.VehicleType.CAR).spots[0].id)
    next_moto_spot = str(garage.get_next_spot(garage.Vehicle.VehicleType.MOTORCYCLE).spots[0].id)

    next_bus_spot = []
    next_bus = garage.get_next_spot(garage.Vehicle.VehicleType.BUS).spots
    for bus_spot in next_bus:
        next_bus_spot.append(bus_spot.id)

    response_dict = {'name': garage.name,
                     'max_capacity': garage.max_capacity,
                     'occupancy': garage.vehicle_count,
                     'cars': garage.car_count,
                     'motorcycles': garage.moto_count,
                     'buses': garage.bus_count,
                     'available': available,
                     'available_spot_types': available_spot_types,
                     'available_spots_total': available_spots_total,
                     'available_spots': available_spots,
                     'assigned_spots': assigned_spots,
                     'next_car_spot': next_car_spot,
                     'next_moto_spot': next_moto_spot,
                     'next_bus_spot': next_bus_spot}

    response.body = response_dict
