class Mkfs(object):

    @classmethod
    def ext4(cls, device, disk_uuid=None):
        uuid_part = f" -U {disk_uuid}" if disk_uuid else ""
        return f"mkfs.ext4 {uuid_part} -F {device}"

    @classmethod
    def xfs(cls, device, disk_uuid=None):
        uuid_part = f" -m uuid={disk_uuid}" if disk_uuid else ""
        return f"mkfs.xfs {uuid_part} -f {device}"

    @classmethod
    def command(cls, device, fstype, **kwargs):
        SUPPORTED_TYPES = {"xfs" : Mkfs.xfs,
                           "ext4" : Mkfs.ext4}
        if fstype not in SUPPORTED_TYPES:
            raise Exception(f"Filesystem {fstype} is not supported")
        return SUPPORTED_TYPES[fstype](device, **kwargs)
