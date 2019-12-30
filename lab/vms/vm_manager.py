import concurrent.futures
import logging


class VMManager(object):

    def __init__(self, loop, libvirt_api, image_store):
        self.loop = loop 
        self.libvirt_api = libvirt_api
        self.image_store = image_store
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    async def _create_storage(self, vm):
        image_path = await self.image_store.clone_qcow(vm['base_image'], vm['name'])
        vm['image'] = image_path

    async def _delete_qcow_no_exception(self, image_path):
        try:
            await self.image_store.delete_qcow(image_path)
        except:
            logging.exception("Failed to delete image %s", image_path)

    async def _delete_storage(self, vm):
        if 'image' in vm:
            await self._delete_qcow_no_exception(vm['image'])
            del vm['image']

    async def allocate_vm(self, vm):
        await self._create_storage(vm)
        try:
            await self.loop.run_in_executor(self.thread_pool,
                                                     lambda: self.libvirt_api.define_vm(vm))
            await self.loop.run_in_executor(self.thread_pool,
                                               lambda: self.libvirt_api.start_vm(vm))
        except:
            logging.error("Failed to create VM %s", vm)
            await self.destroy_vm(vm)
            await self._delete_storage(vm)
            raise
        else:
            return vm

    async def destroy_vm(self, vm):
        await self.loop.run_in_executor(self.thread_pool,
                                        lambda: self.libvirt_api.kill_by_name(vm["name"]))
        await self._delete_storage(vm)

