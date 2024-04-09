import unittest
import json
import os.path
from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient
from filip.models import FiwareHeader
from filip.models.ngsi_v2.context import ContextEntity
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

        # device list
        self.devices_list = [
            {
                "ID": "eui-a81758fffe045eea",
                "sensor_type": "Elsys ERS CO2"
            },
            {
                "ID": "eui-a81758fffe045ef3",
                "sensor_type": "Elsys ERS CO2"
            },
            {
                "ID": "eui-a81758fffe045eee",
                "sensor_type": "Elsys ERS CO2"
            },
            {
                "ID": "eui-a81758fffe045f59",
                "sensor_type": "Elsys ERS CO2"
            },
            {
                "ID": "eui-10ce45fffe007e89",
                "sensor_type": "AME"
            },
            {
                "ID": "eui-10ce45fffe007e70",
                "sensor_type": "AME"
            },
            {
                "ID": "eui-10ce45fffe007e6e",
                "sensor_type": "AME"
            },
            {
                "ID": "eui-10ce45fffe007e6c",
                "sensor_type": "AME"
            },
            {
                "ID": "eui-0018b2400001a3fb",
                "sensor_type": "Adeunis modbus"
            }
        ]

    def test_data_model_provision(self):
        # 1. load devices from excel table
        pass

        # 2. provisioning
        for device_item in self.devices_list:
            _uid = device_item["ID"]
            device_type = device_item["sensor_type"]
            # create entity
            with open(os.path.join(path_input, "entity_templates",
                                   device_type + ".json")) as f:
                entity_template: dict = json.load(f)
                entity_template['id'] = f"{entity_template['type']}:{_uid}"
                entity = ContextEntity(**entity_template)
                with self.cb_client:
                    self.cb_client.post_entity(entity)
                    entity_fiware = self.cb_client.get_entity(entity_id=entity.id)
                    self.assertEqual(entity_fiware.id, entity_template.get('id'))

            # create device
            with open(os.path.join(path_input, "device_templates",
                                   device_type + ".json")) as f:
                device_template: dict = json.load(f)
                device_template['device_id'] = _uid
                device_template['entity_name'] = f"{entity_template['type']}:{_uid}"
                device = Device(**device_template)
                # test the connection
                with self.iotc:
                    self.iotc.post_device(device=device)
                    device_fiware = self.iotc.get_device(device_id=device.device_id)
                    self.assertEqual(device_fiware.device_id,
                                     device_template.get('device_id'))

        # 3. validate provisioning
        for device in self.iotc.get_device_list():
            entity = self.cb_client.get_entity(entity_id=device.entity_name)
            for attr in device.attributes:
                entity_attr = entity.get_attribute(attr.name)
                self.assertEqual(entity_attr.type, attr.type)

    def test_append_attribute(self):
        pass

    def test_delete_attribute(self):
        pass

    def test_rename_attribute(self):
        pass

    def test_anonymous_update(self):
        pass

    def tearDown(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )

        clear_all(fiware_header=self.fiware_header,
                  cb_url=settings.CB_URL,
                  iota_url=settings.IOTA_JSON_URL
                  )
        self.iotc.close()
        self.cb_client.close()


if __name__ == "__main__":
    unittest.main()
