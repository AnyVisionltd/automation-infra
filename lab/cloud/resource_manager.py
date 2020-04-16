import logging
import sys
import time

from aiohttp import web
from python_terraform import *
import boto3

GCE_PROJECT = "/root/terraform/projects/setup-single-instance-gcp-terraform"
AWS_PROJECT = "/root/terraform/projects/setup-multiple-empty-instances-aws-terraform"


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

OWNER_NAME = os.environ.get("OWNER_NAME", "il_cloud_resource_manager")


class CloudResourceManager(object):

    def __init__(self):
        webapp = web.Application()
        webapp.router.add_routes([web.post('/provision', self.provision_instance),
                                  web.get('/instances', self.handle_list_instances),
                                  web.post('/destroy', self.destroy_instance)])
        web.run_app(webapp)

    async def handle_list_instances(self, request):
        data = await request.json()
        customer_name, region = data.get("customer_name"), data.get("region")
        client = boto3.client('ec2', region_name=region)
        response = client.describe_instances(
            Filters=[
                {'Name': 'tag:customer_name', 'Values': [customer_name]},
                {'Name': 'tag:owner_name', 'Values': [OWNER_NAME]}
            ],
            DryRun=False,
            MaxResults=500
        )
        print(response)
        result = []
        if response["Reservations"] and response["Reservations"][0]:
            for instance in response["Reservations"]:
                instance_details = instance.get("Instances")[0]
                instance_type = instance_details.get("InstanceType")
                image_ami = instance_details.get("ImageId")
                public_ip = instance_details.get("PublicIpAddress")
                result.append({"instance_type": instance_type, "image_ami": image_ami, "public_ip": public_ip})
                print(instance_type, image_ami, public_ip)
            return web.json_response({'instances': result}, status=200)
        else:
            return web.json_response({'msg': f"Instance {customer_name}-{OWNER_NAME} NOT found in {region}"}, status=200)

    async def provision_instance(self, request):
        data = await request.json()

        customer_name, region = data.get("customer_name"), data.get("region")
        terraform_vars = {
            "customer_name": customer_name,
            "owner_name": OWNER_NAME,
            "keypair": data.get("keypair", "anyvision-devops"),
            "environment_type": "automation",
            "region": region,
            "instance_type": data["instance_type"],
            "ssd_ebs_size": data["ssd_ebs_size"],
            "storage_ebs_size": data["storage_ebs_size"]
        }
        logger.info(f"Provision {data}")
        tf = Terraform(working_dir=AWS_PROJECT)
        state_file_path = 'automation/{}/{}/{}'.format(OWNER_NAME, customer_name, region)
        logger.info(f'Initiating state file to bucket tf-state-anyvision/{state_file_path}')
        start = time.time()
        return_code, stdout, stderr = tf.init(backend_config={'key': state_file_path})
        if return_code !=0:
            logger.error(f"Error: {stderr}")
            logger.debug("Init Terraform failed")
            return web.json_response({'status': f'Provision Failed with msg {stderr}'}, status=500)
        logger.info("Applying config")
        return_code, stdout, stderr = tf.apply(dir_or_plan=AWS_PROJECT, capture_output=True, input=False,
                                               skip_plan=True, var=terraform_vars)
        if return_code != 0:
            logging.exception("Failed to provision VM")
            return web.json_response({'status': f'Provision Failed with msg {stderr}'}, status=500)
        else:
            ip_address = tf.output()["instances_public_ips"]["value"][0]
            return web.json_response({'status': 'Success', 'name': f"{customer_name}-{OWNER_NAME}", "ip": ip_address,
                                      "time": time.time() - start}, status=200)

    async def destroy_instance(self, request):
        data = await request.json()
        tf = Terraform(working_dir=AWS_PROJECT)
        customer_name, region = data.get("customer_name"), data.get("region")
        terraform_vars = {"customer_name": customer_name, "owner_name": OWNER_NAME, "region": region}
        state_file_path = 'automation/{}/{}/{}'.format(OWNER_NAME, customer_name, region)
        start = time.time()
        return_code, stdout, stderr = tf.init(backend_config={'key': state_file_path, 'bucket': 'tf-state-anyvision'})
        if return_code != 0:
            return web.json_response({'status': 'Failed', 'msg': 'Failed to Initiate Destroy'}, status=500)
        return_code, stdout, stderr = tf.destroy(auto_approve=True, var=terraform_vars)
        if return_code != 0:
            logging.exception("Failed to destroy VM")
            return web.json_response({'status': 'Failed to Destroy Instance'}, status=500)
        else:
            return web.json_response({'status': 'Success', 'msg': f"{customer_name}-{OWNER_NAME} Destroyed",
                                      "time": time.time() - start}, status=200)


if __name__ == '__main__':
    CloudResourceManager()