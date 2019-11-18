import logging

from src.garage.api.garage import (Garage,
                                   build_garage_doc,
                                   write_garage_doc)
from src.garage.utils import (validate_request_body,
                              APIError,
                              status_codes)

logger = logging.getLogger(__name__)


# create instance of Garage object from json file
def get_garage_data(fn='main_garage_v1.json'):
    return build_garage_doc(fn=fn)


def update_garage_data(garage, fn='main_garage_v1.json'):
    return write_garage_doc(fn, garage)


def http_put(request, response, params, document=None):
    """ Resource = garage/v1/parking """

    if not document:
        logger.debug('Loading garage document')
        document = get_garage_data()

    # create instance of Garage object from json file
    logger.debug('Instantiating Garage class object')
    garage = Garage(document)

    # check the garage overall availability
    logger.debug('Checking available status')
    if garage.available:

        # validate request body
        validate_request_body(request.body,
                              required_params={'vehicle_type': int})

        # validate vehicle type
        selected_vehicle_type = request.body['vehicle_type']
        if not garage.Vehicle.VehicleType(selected_vehicle_type):
            raise APIError(code='Invalid Vehicle Type',
                           cause='Invalid Vehicle Type',
                           message='Please enter correct Vehicle Type',
                           status=status_codes.HTTP_BAD_REQUEST)

        # get new vehicle id from vehicle counter
        # instantiate new vehicle object

        logger.debug('Creating Vehicle')
        vehicle = garage.set_vehicle(selected_vehicle_type)

        # look for available spot for this vehicle type
        logger.debug('Getting Spot for Vehicle')
        available = garage.get_next_spot(vehicle.vehicle_type)
        if available.spots:
            # place vehicle object in spot object
            garage.assign_spot(available, vehicle)

            # format assigned spot for readability
            spots = garage.format_spot(available.spots)

            # populate response dict
            response_dict = {'vehicle_id': vehicle.id,
                             'vehicle_type': vehicle.vehicle_type.name,
                             'level': available.level.id,
                             'row': available.row.id,
                             'spot_id': spots['spot_id'],
                             'spot_type': spots['spot_type']}

            # update garage document
            update_garage_data(garage=garage)

        # else here means that no spot permissible for this vehicle type was found
        else:
            raise APIError(code='Full for Vehicle Type: ' + vehicle.vehicle_type.name,
                           cause='Full for Vehicle Type: ' + vehicle.vehicle_type.name,
                           message='Please come again',
                           status=status_codes.HTTP_BAD_REQUEST)

    # else here means that the garage is not available, and is marked as such
    else:
        raise APIError(code='Garage Full',
                       cause='Garage Full',
                       message='Please come again',
                       status=status_codes.HTTP_BAD_REQUEST)

    response.status = status_codes.HTTP_CREATED
    response.body = response_dict


def http_delete(request, response, params, document=None):
    """ Resource = garage/v1/parking """
    if not document:
        logger.debug('Loading garage document')
        document = get_garage_data()

    # create instance of Garage object from json file
    logger.debug('Instantiating Garage class object')
    garage = Garage(document)

    # validate request body
    validate_request_body(request.body,
                          required_params={'vehicle_id': str,
                                           'spot_id': str,
                                           'row': str,
                                           'level': str})

    selected_vehicle = request.body['vehicle_id']
    selected_spots = garage.decouple_spot_id(request.body['spot_id'])
    selected_row = request.body['row']
    selected_level = request.body['level']
    location = Garage.Location

    logger.debug('Checking assigned vehicle ids')
    if selected_vehicle not in garage.assigned_ids:
        raise APIError(code='Invalid Vehicle ID',
                       cause='Invalid Vehicle ID',
                       message='Please enter correct Vehicle ID',
                       status=status_codes.HTTP_NOT_FOUND)

    logger.debug('Checking location')
    if selected_level in garage.levels:
        location.level = garage.levels[selected_level]
    else:
        raise APIError(code='Invalid Level ID',
                       cause='Invalid Level ID',
                       message='Please enter correct Level ID',
                       status=status_codes.HTTP_BAD_REQUEST)

    if selected_row in garage.levels[selected_level].rows:
        location.row = garage.levels[selected_level].rows[selected_row]
    else:
        raise APIError(code='Invalid Row ID',
                       cause='Invalid Row ID',
                       message='Please enter correct Row ID',
                       status=status_codes.HTTP_BAD_REQUEST)

    valid_spots = []
    for spot in selected_spots:
        # spot = garage.levels[selected_level].rows[selected_row].spots[spot]
        if spot in garage.levels[selected_level].rows[selected_row].spots:
            valid_spots.append(garage.levels[selected_level].rows[selected_row].spots[spot])
    if not valid_spots:
        raise APIError(code='Invalid Spot ID',
                       cause='Invalid Spot ID',
                       message='Please enter correct Spot ID',
                       status=status_codes.HTTP_BAD_REQUEST)
    else:
        location.spots = valid_spots
        logger.debug('Checking for vehicle in locaton')
        vehicle_in_location = garage.check_spot(location)
        if vehicle_in_location.id != selected_vehicle:
            raise APIError(code='Vehicle Not in Spot',
                           cause='Vehicle Not in Spot',
                           message='Please enter correct Spot ID or Vehicle ID',
                           status=status_codes.HTTP_BAD_REQUEST)
        else:
            logger.debug('Unassigning vehicle')
            garage.unassign_spot(location, vehicle_in_location)
            logger.debug('Updating garage document')
            update_garage_data(garage=garage)
