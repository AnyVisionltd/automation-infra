import logging
import sys
from aiohttp import web
from python_terraform import *

GCE_PROJECT = "/root/terraform/projects/setup-single-instance-gcp-terraform"
AWS_PROJECT = "/root/terraform/projects/setup-multiple-empty-instances-aws-terraform"


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class CloudResourceManager(object):

    def __init__(self):
        webapp = web.Application()
        webapp.router.add_routes([web.post('/provision', self.provision_instance),
                                  web.post('/destroy', self.destroy_instance)])
        web.run_app(webapp)

    async def provision_instance(self, request):
        data = await request.json()

        terraform_vars = {
            "customer_name": data["owner_name"],
            "owner_name": data["owner_name"],
            "keypair": data.get("keypair", "devops-aws"),
            "environment_type": "automation",
            "region": data["region"],
            "instance_type": data["instance_type"],
            "ssd_ebs_size": 200,
            "storage_ebs_size": 500
        }
        logger.info(f"Provision {data}")
        tf = Terraform(working_dir=AWS_PROJECT)
        state_file_path = 'automation/{}/{}'.format(data.get('region'), data.get('owner_name'))
        logger.info(f'Initiating state file to bucket tf-state-anyvision/{state_file_path}')
        return_code, stdout, stderr = tf.init(backend_config={'key': state_file_path })
        if return_code !=0:
            logger.error(f"Error: {stderr}")
            logger.debug("Init Terraform failed")
            return web.json_response({'status': f'Provision Failed with msg {stderr}'}, status=500)
        logger.info("Applying config")
        return_code, stdout, stderr = tf.apply(dir_or_plan=AWS_PROJECT, capture_output=False, auto_approve=True, input=False,
                                               skip_plan=True, var=terraform_vars)
        if return_code != 0:
            logging.exception("Failed to provision VM")
            return web.json_response({'status': f'Provision Failed with msg {stderr}'}, status=500)
        else:
            ip_address = tf.output()["instances_public_ips"]["value"][0]
            return web.json_response({'status': 'Success', 'name': "ec2-{}.".format(data["owner_name"]), "ip": ip_address}, status=200)

    async def destroy_instance(self, request):
        data = await request.json()
        tf = Terraform(working_dir=AWS_PROJECT)
        state_file_path = 'automation/{}/{}'.format(data.get('region'), data.get('owner_name'))
        return_code, stdout, stderr = tf.init(backend_config={'key': state_file_path})
        if return_code != 0:
            return web.json_response({'status': 'Failed to Initiate Destroy '}, status=500)
        return_code, stdout, stderr = tf.destroy(auto_approve=True)
        if return_code != 0:
            logging.exception("Failed to destroy VM")
            return web.json_response({'status': 'Failed to Destroy Instance'}, status=500)
        else:
            return web.json_response({'status': 'Success', 'msg': "ec2-{} Destroyed".format(data["owner_name"])}, status=200)


if __name__ == '__main__':
    CloudResourceManager()

