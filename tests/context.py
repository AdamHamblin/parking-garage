
import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
project_root, tail = os.path.split(dir_path)
sys.path.insert(0, os.path.abspath(os.path.join(project_root, '..')))

from src.garage.api.garage import build_garage_doc, Garage
from src.garage.api.parking import http_put, http_delete
from src.garage.api.status import http_get
from src.garage.utils import APIError, status_codes
from tests.common import Request, Response
