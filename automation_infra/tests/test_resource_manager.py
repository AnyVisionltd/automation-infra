import logging

from automation_infra.plugins.resource_manager import ResourceManager
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    manager = base_config.hosts.host.ResourceManager
    anv_testing_bucket = "anyvision-testing"
    files = manager.get_s3_files(anv_testing_bucket, "")
    manager.upload_from_filesystem("media/high_level_design.xml", "temp/")
    assert manager.file_exists(anv_testing_bucket, "temp/high_level_design.xml")
    manager.delete_file(anv_testing_bucket, 'temp/high_level_design.xml')
    assert not manager.file_exists(anv_testing_bucket, "temp/high_level_design.xml")
    logging.info("<<<<<<<<<RESOURCE_MANAGER PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>>>>>>")
