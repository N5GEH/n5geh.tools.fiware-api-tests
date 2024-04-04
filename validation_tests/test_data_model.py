import json
import os.path
from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient
from filip.models import FiwareHeader
import pandas as pd
from settings import settings


path_input = "inputs/test_data_model"

if __name__ == "__main__":
    # 0. Initial client
    fiware_header = FiwareHeader(
        service=settings.FIWARE_SERVICE,
        service_path=settings.FIWARE_SERVICEPATH,
    )
    cb_client = ContextBrokerClient(url=settings.CB_URL,
                                    fiware_header=fiware_header)
    iotc = IoTAClient(url=settings.IOTA_URL,
                      fiware_header=fiware_header)

    # 1. load devices from excel table
    devices_df = pd.read_excel("inputs/test_data_model/devices.xlsx")
    for index, row in devices_df.iterrows():
        _uid = row["ID"]
        device_type = row["sensor_type"]
        # create entity
        with open(os.path.join(path_input, "entity_templates", device_type+".json")) as f:
            entity_template: dict = json.load(f)

        # create device
        with open(os.path.join(path_input, "device_templates", device_type+".json")) as f:
            device_template: dict = json.load(f)

