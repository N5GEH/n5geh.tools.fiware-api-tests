from pydantic import AnyUrl, AnyHttpUrl, Field, AliasChoices
from pydantic_settings import BaseSettings
from typing import Union, Optional


class TestSettings(BaseSettings):
    """
    Settings for the test case scenarios according to pydantic's documentaion
    https://pydantic-docs.helpmanual.io/usage/settings/
    """
    LOG_LEVEL: str = Field(default="ERROR",
                           validation_alias=AliasChoices('LOG_LEVEL', 'LOGLEVEL'))

    CB_URL: AnyHttpUrl = Field(default="http://localhost:1026",
                               validation_alias=AliasChoices('ORION_URL',
                                                             'CB_URL',
                                                             'CB_HOST',
                                                             'CONTEXTBROKER_URL',
                                                             'OCB_URL'))
    IOTA_URL: AnyHttpUrl = Field(default="http://localhost:4041",
                                 validation_alias='IOTA_URL')
    IOTA_JSON_URL: AnyHttpUrl = Field(default="http://localhost:4041",
                                      validation_alias='IOTA_JSON_URL')

    IOTA_UL_URL: AnyHttpUrl = Field(default="http://127.0.0.1:4061",
                                    validation_alias=AliasChoices('IOTA_UL_URL'))

    QL_URL: AnyHttpUrl = Field(default="http://127.0.0.1:8668",
                               validation_alias=AliasChoices('QUANTUMLEAP_URL',
                                                             'QL_URL'))

    MQTT_BROKER_URL: AnyUrl = Field(default="mqtt://127.0.0.1:1883",
                                    validation_alias=AliasChoices(
                                        'MQTT_BROKER_URL',
                                        'MQTT_URL',
                                        'MQTT_BROKER'))

    MQTT_BROKER_URL_INTERNAL: AnyUrl = Field(default="mqtt://mosquitto:1883",
                                             validation_alias=AliasChoices(
                                                 'MQTT_BROKER_URL_INTERNAL',
                                                 'MQTT_URL_INTERNAL'))

    # IF CI_JOB_ID is present it will always overwrite the service path
    # TODO might not necessary
    CI_JOB_ID: Optional[str] = Field(default=None,
                                     validation_alias=AliasChoices('CI_JOB_ID'))

    # create service paths for multi tenancy scenario and concurrent testing
    FIWARE_SERVICE: str = Field(default="filip",
                                validation_alias=AliasChoices('FIWARE_SERVICE'))

    FIWARE_SERVICEPATH: str = Field(default="/",
                                    validation_alias=AliasChoices('FIWARE_PATH',
                                                                  'FIWARE_SERVICEPATH',
                                                                  'FIWARE_SERVICE_PATH'))


settings = TestSettings()
