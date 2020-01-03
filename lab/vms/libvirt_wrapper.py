import libvirt
import logging
from . import vm_template
from contextlib import contextmanager


class LibvirtWrapper(object):

    def __init__(self, connection_uri):
        self.connection_uri = connection_uri

    @contextmanager
    def _libvirt_connection(self):
        connection = None
        try:
            connection = libvirt.open(self.connection_uri)
            yield connection
        except Exception as e:
            logging.exception("Libvirt operation failed")
            raise e
        finally:
            if connection is not None:
                connection.close()

    def define_vm(self, machine_info):
        with self._libvirt_connection() as connection:
            xml = vm_template.generate_xml(machine_info)
            logging.info("Defined vm %(name)s, xml: \n %(xml)s", dict(name=machine_info.name, xml=xml))
            connection.defineXML(xml)

    def start_vm(self, machine_info):
        name = machine_info['name']
        with self._libvirt_connection() as connection:
            vm = connection.lookupByName(name)
            vm.create()
        logging.info("started vm %s", name)

    def poweroff_vm(self, machine_info):
        name = machine_info['name']
        with self._libvirt_connection() as connection:
            vm = connection.lookupByName(name)
            vm.destroy()
        logging.info("VM %s destroyed", name)

    def kill_by_name(self, name):
        logging.debug("killimg vm %s", name)
        with self._libvirt_connection() as connection:
            try:
                vm = connection.lookupByName(name)
            except libvirt.libvirtError:
                logging.warning("VM %s is not found", name)
                return
            if vm.isActive():
                logging.info("vm is active")
                vm.destroy()
            vm.undefine()
