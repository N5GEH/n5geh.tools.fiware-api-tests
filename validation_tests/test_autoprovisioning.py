import json
import time
import unittest

from paho.mqtt.client import Client, CallbackAPIVersion
from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient
from filip.models import FiwareHeader
from filip.models.ngsi_v2.iot import ServiceGroup, DeviceAttribute, Device
from filip.utils.cleanup import clear_all

from settings import settings

path_input = "inputs/test_autoprovisioning"

standard_entity = {
    "id": "Entity:001",
    "type": "Entity",
    "attribute1": {
        "type": "Number",
        "value": 1
    },
    "attribute2": {
        "type": "Number",
        "value": 2
    },
    "attribute3": {
        "type": "Number",
        "value": 3
    },
    "attribute4": {
        "type": "Number",
        "value": 4
    }
}

standard_device = {
    "device_id": "Device:001",
    "entity_name": standard_entity["id"],
    "entity_type": standard_entity["type"],
    "transport": "MQTT",
    "explicitAttrs": True,
    "attributes": [
        {
            "name": "attribute1",
            "type": "Number",
            "object_id": "a1"
        },
        {
            "name": "attribute2",
            "type": "Number",
            "object_id": "a2"
        },
        {
            "name": "attribute3",
            "type": "Number",
            "object_id": "a3"
        },
        {
            "name": "attribute4",
            "type": "Number",
            "object_id": "a4"
        }
    ]
}

standard_service_group = {
    "resource": "/iot/json",
    "apikey": "fiware-api-test",
    "explicitAttrs": True,
    "autoprovision": False
}


class TestAutoprovisioning(unittest.TestCase):

    def setUp(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )

        self.cb_client = ContextBrokerClient(url=settings.CB_URL,
                                             fiware_header=self.fiware_header)
        self.iotc = IoTAClient(url=settings.IOTA_JSON_URL,
                               fiware_header=self.fiware_header)

        self.mqttc = Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self.mqttc.username_pw_set(username=settings.MQTT_USERNAME,
                                   password=settings.MQTT_PASSWORD)
        if settings.MQTT_TLS:
            self.mqttc.tls_set()
        self.mqttc.connect(host=settings.MQTT_BROKER_URL.host,
                           port=settings.MQTT_BROKER_URL.port)

        # TODO: clean up

        # clear_all(fiware_header=self.fiware_header,
        #           cb_url=settings.CB_URL,
        #           iota_url=settings.IOTA_JSON_URL,
        #           ql_url=settings.QL_URL,)

        # TODO: Create service group



    def test_autoprovision(self):

        # TODO: Send data for a non existing device
        # TODO: Check if device is created
        # TODO: Check if entity is created
        # TODO: Check if entity holds the right data
        pass

    def test_cross_group_operation_with_autoprov(self):
        # create 3 service groups, each with a device?
        # group 1
        attr1 = DeviceAttribute(
            name="attribute1",
            type="Number",
            object_id="a1"
        )
        device1_id = "Device:001"
        sg1 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-1",
            autoprovision=True,
            explicitAttrs=False,
            entity_type="Type1",
            attributes=[attr1]
        )

        # group 2
        attr2 = DeviceAttribute(
            name="attribute2",
            type="Number",
            object_id="a2"
        )
        device2_id = "Device:002"
        sg2 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-2",
            autoprovision=True,
            explicitAttrs=False,
            entity_type="Type2",
            attributes=[attr2]
        )
        # create device 2
        self.iotc.post_device(
            device=Device(**{
            "device_id": device2_id,
            "entity_name": "Entity:002",
            "entity_type": "Type2",
            "transport": "MQTT",
            "attributes": [attr2]
        }))

        # group 3
        attr3 = DeviceAttribute(
            name="attribute3",
            type="Number",
            object_id="a3"
        )
        device3_id = "Device:003"
        sg3 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-3",
            entity_type="Type3",
            autoprovision=True,
            explicitAttrs=False,
            attributes=[attr3]
        )

        # create service groups in IoT Agent
        self.iotc.post_groups([sg1, sg2, sg3])

        # update device 1 with group 2 credentials. and 2 -> 3, 3 -> 1
        for device, attr, sg in zip([device1_id, device2_id, device3_id], [attr1, attr2, attr3], [sg2, sg3, sg1]):
        # for device, attr, sg in zip([device1_id, device2_id, device3_id], [attr1, attr2, attr3], [sg1, sg2, sg3]):
            iot_topic = f"/json/{sg.apikey}/{device}/attrs"
            self.mqttc.publish(
                topic=iot_topic,
                payload=json.dumps({
                    attr.object_id: 10
                })
            )

        # verify the results
        time.sleep(2)
        devices = self.iotc.get_device_list()
        entities = self.cb_client.get_entity_list()
        for entity in entities:
            if entity.id == "Entity:002":  # attribute update will work with not matching service group if device exists
                self.assertIn('"value":10.0', entity.model_dump_json())
            else:  # Attribute update will not work with not matching service group
                self.assertNotIn('"value":10.0', entity.model_dump_json())

        # update new device 1 with correct group credentials  -> works
        device1_id_new = "Device:001:NEW"
        iot_topic = f"/json/{sg1.apikey}/{device1_id_new}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr1.object_id: 15
            })
        )
        # verify the results
        time.sleep(2)
        entity_1_new = self.cb_client.get_entity_list(id_pattern=device1_id_new)[0]
        self.assertIn('"value":15', entity_1_new.model_dump_json())

    def test_cross_group_operation_without_autoprov(self):
        # test with without autoprovision
        attr4 = DeviceAttribute(
                    name="attribute4",
                    type="Number",
                    object_id="a4"
                )
        sg4 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-4",
            entity_type="Type4",
            autoprovision=True,
            explicitAttrs=False,
            # attributes=[attr4]
        )
        self.iotc.post_groups([sg4])

        attr5 = DeviceAttribute(
                    name="attribute5",
                    type="Number",
                    object_id="a5"
                )
        sg5 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-5",
            entity_type="Type5",
            autoprovision=False,
            explicitAttrs=False,
            attributes=[attr5]
        )
        self.iotc.post_groups([sg5])

        attr6 = DeviceAttribute(
                    name="attribute6",
                    type="Number",
                    object_id="a6"
                )
        sg6 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-6",
            entity_type="Type6",
            autoprovision=False,
            explicitAttrs=True,
            attributes=[attr6]
        )
        self.iotc.post_groups([sg6])

        # create device4
        device4_id = "Device:004"
        self.iotc.post_device(
            device=Device(**{
            "device_id": device4_id,
            "entity_name": "Entity:004",
            "entity_type": "Type4",
            "transport": "MQTT",
            "explicitAttrs": False,
            "attributes": [attr4]
        }))

        # update device4 with wrong service group, explicitAttrs=False -> will work
        iot_topic = f"/json/{sg5.apikey}/{device4_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr4.object_id: 20
            })
        )
        # verify the results
        time.sleep(2)
        entity_4 = self.cb_client.get_entity(entity_id="Entity:004")
        self.assertIn('"value":20', entity_4.model_dump_json())

        # add a new attribute with right service group, explicitAttrs=False -> TODO should work but currently not, since a patch request is sent
        # TODO seems like undefined attribute can not be added
        iot_topic = f"/json/{sg4.apikey}/{device4_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr5.object_id: 25
            })
        )
        # verify the results
        time.sleep(2)
        entity_4 = self.cb_client.get_entity(entity_id="Entity:004")
        self.assertNotIn('"value":25', entity_4.model_dump_json())

        # update device4 attribute with wrong service group, explicitAttrs=True -> will work
        iot_topic = f"/json/{sg6.apikey}/{device4_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr4.object_id: 30
            })
        )
        # verify the results
        time.sleep(2)
        entity_4 = self.cb_client.get_entity(entity_id="Entity:004")
        self.assertIn('"value":30', entity_4.model_dump_json())

        # add a new attribute with wrong service group, explicitAttrs=True -> will NOT work
        iot_topic = f"/json/{sg6.apikey}/{device4_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr6.object_id: 35
            })
        )
        # verify the results
        time.sleep(2)
        entity_4 = self.cb_client.get_entity(entity_id="Entity:004")
        self.assertNotIn('"value":35', entity_4.model_dump_json())


    def test_different_transport(self):
        # create one http transport

        # provision device in http transport

        # create one mqtt transport

        # provision device in mqtt transport

        # update mqtt device with mqtt

        # update http device with mqtt

        pass

    def tearDown(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )
        clear_all(cb_client=self.cb_client,
                  iota_client=self.iotc)
        self.iotc.close()
        self.cb_client.close()


if __name__ == "__main__":
    unittest.main()
