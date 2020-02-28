import concurrent.futures
import logging
import string
import uuid
import asyncio


class VMManager(object):

    def __init__(self, loop, libvirt_api, image_store, disk_privisoner):
        self.loop = loop 
        self.libvirt_api = libvirt_api
        self.image_store = image_store
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self.disk_privisoner = disk_privisoner
        # "sda" is taken for boot drive
        self.vol_names = ["sd%s" % letter for letter in  string.ascii_lowercase[1:]]

    async def _create_vm_boot_disk(self, vm):
        vm.image = await self.image_store.clone_qcow(vm.base_image, vm.name)

    async def _create_storage(self, vm):
        image_path = await self.image_store.clone_qcow(vm.base_image, vm.name)
        vm.image = image_path

        for i, disk in enumerate(vm.disks):
            disk['serial'] = str(uuid.uuid4())
            disk['device_name'] = self.vol_names[i]
            disk['image'] = await self.image_store.create_qcow(vm.name, disk['type'], disk['size'], disk['serial'])
            await self.loop.run_in_executor(self.thread_pool,
                                            lambda: self.disk_privisoner.provision_disk(disk['image'], disk['fs'], disk['serial']))

    async def verify_storage_valid(self, vm):
        try:
            await self.image_store.qcow_info(vm.image)
            for disk in vm.disks:
                await self.image_store.qcow_info(disk['image'])
        except:
            logging.warning("Failed to verify storate validity for vm %s", vm, exc_info=True)
            return False
        else:
            return True

    async def _delete_qcow_no_exception(self, image_path):
        try:
            await self.image_store.delete_qcow(image_path)
        except:
            logging.exception("Failed to delete image %s", image_path)

    async def _delete_storage(self, vm):
        if vm.image is not None:
            await self._delete_qcow_no_exception(vm.image)

        for disk in vm.disks:
            if 'image' in disk:
                await self._delete_qcow_no_exception(disk['image'])

    async def allocate_vm(self, vm):
        try:
            await self._create_storage(vm)
            await self.loop.run_in_executor(self.thread_pool,
                                                     lambda: self.libvirt_api.define_vm(vm))
            await self.start_vm(vm)
        except Exception as e:
            logging.error("Failed to create VM %s", vm)
            try:
                await self.destroy_vm(vm)
                await self._delete_storage(vm)
            except:
                logging.exception("Error during vm destroy of %s", vm.name)
            raise e
        else:
            return vm

    async def start_vm(self, vm):
        logging.debug("Starting vm %s", vm.name)
        await self.loop.run_in_executor(self.thread_pool,
                                               lambda: self.libvirt_api.start_vm(vm))

    async def stop_vm(self, vm):
        logging.debug("Stopping vm %s", vm.name)
        await self.loop.run_in_executor(self.thread_pool,
                                               lambda: self.libvirt_api.poweroff_vm(vm))

    async def destroy_vm(self, vm):
        logging.info("Deleting vm %s", vm)
        try:
            await self.loop.run_in_executor(self.thread_pool,
                                            lambda: self.libvirt_api.kill_by_name(vm.name))
            await self._delete_storage(vm)
        except:
            raise

    async def _result_or_default(self, func, default):
        try:
            return await self.loop.run_in_executor(self.thread_pool, func)
        except:
            return default

    async def info(self, vm):
        net_info, status = await asyncio.gather(
                            self._result_or_default(lambda: self.libvirt_api.dhcp_lease_info(vm.name), {}),
                            self._result_or_default(lambda: self.libvirt_api.status(vm.name), "Fail"))
        return {'name': vm.name,
                'disks': [{'type': disk['type'],
                           'size': disk['size'],
                           'serial': disk['serial']} for disk in vm.disks],
                'status': status,
                'dhcp': net_info}

    async def vm_status(self, vm):
        status = await self._result_or_default(lambda: self.libvirt_api.status(vm.name), "Fail")
        logging.info("vm info %s", status)
        return status

    async def load_vms_data(self):
        logging.info("Loading vms from libvirt")
        return await self._result_or_default(lambda: self.libvirt_api.load_lab_vms(), [])

