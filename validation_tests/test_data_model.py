import unittest
import json
import os.path
from time import sleep

from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient
from filip.models import FiwareHeader
import pandas as pd
from filip.models.ngsi_v2.context import ContextEntity, ContextAttribute
from filip.models.ngsi_v2.iot import Device
from filip.utils.cleanup import clear_all

from settings import settings

path_input = "inputs/test_data_model"


class TestDataModel(unittest.TestCase):

    def setUp(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )

        clear_all(fiware_header=self.fiware_header,
                  cb_url=settings.CB_URL,
                  iota_url=settings.IOTA_JSON_URL
                  )

        # Initial client
        self.cb_client = ContextBrokerClient(url=settings.CB_URL,
                                             fiware_header=self.fiware_header)
        self.iotc = IoTAClient(url=settings.IOTA_JSON_URL,
                               fiware_header=self.fiware_header)

    def test_data_model(self):
        # 1. load devices from excel table
        devices_df = pd.read_excel("inputs/test_data_model/devices.xlsx")
        for index, row in devices_df.iterrows():
            _uid = row["ID"]
            device_type = row["sensor_type"]
            # create entity
            with open(os.path.join(path_input, "entity_templates",
                                   device_type + ".json")) as f:
                entity_template: dict = json.load(f)
                entity_template['id'] = _uid
                entity = ContextEntity(id=entity_template.get('id'),
                                       type=entity_template.get('type'))
                for key, value in entity_template.items():
                    if key == "id" or key == "type":
                        continue
                    attrs = ContextAttribute(**{key: value})
                    entity.add_attributes({key: attrs})
                # 3. test the connection by sending some data
                with self.cb_client:
                    self.cb_client.post_entity(entity)
                    entity_fiware = self.cb_client.get_entity(entity_id=entity.id)
                    self.assertEqual(entity_fiware.id, entity_template.get('id'))

            # create device
            with open(os.path.join(path_input, "device_templates",
                                   device_type + ".json")) as f:
                device_template: dict = json.load(f)
                device_template['device_id'] = _uid
                device_template['entity_name'] = _uid
                device = Device(**device_template)
                # 3. test the connection by sending some data
                with self.iotc:
                    self.iotc.post_device(device=device)
                    device_fiware = self.iotc.get_device(device_id=device.device_id)
                    self.assertEqual(device_fiware.device_id,
                                     device_template.get('device_id'))


if __name__ == "__main__":
    unittest.main()
