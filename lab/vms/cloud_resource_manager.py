from aiohttp import web
from python_terraform import *

GCE_PROJECT = "/root/terraform/projects/setup-single-instance-gcp-terraform"
AWS_PROJECT = "/root/terraform/projects/setup-multiple-empty-instances-aws-terraform"


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
            "environment_type": "automation",
            "region": data["region"],
            "instance_type": data["instance_type"],
            "os_type": data["os_type"],
            "ssd_ebs_size": 200,
            "storage_ebs_size": 500
        }

        tf = Terraform(working_dir=AWS_PROJECT)
        return_code, stdout, stderr = tf.apply(dir_or_plan=AWS_PROJECT, capture_output=True, auto_approve=True,
                                               input=False,
                                               skip_plan=True, var=terraform_vars)
        ip_address = tf.output()["instances_public_ips"]["value"][0]
        if return_code != 0:
            logging.exception("Failed to provision VM")
            return web.json_response({'status': f'Provision Failed with msg {stderr}'}, status=500)
        else:
            return web.json_response(
                {'status': 'Success', 'name': "ec2-{}.".format(data["owner_name"]), "ip": ip_address}, status=200)

    async def destroy_instance(self, request):
        data = await request.json()
        owner_name = data["owner_name"]
        terraform_vars = {
            "prefix": "terraform/%s/automation/%s" % (data["region_name"], owner_name)

        }
        tf = Terraform(working_dir=AWS_PROJECT)
        return_code, stdout, stderr = tf.init(
            backend_config={"prefix": terraform_vars.get("prefix"), "backend": "gcs", "bucket": "tf-state-anyvision"})
        approve = {"auto_approve": True, "capture_output": False}
        tf.destroy(**approve)
        if return_code != 0:
            logging.exception("Failed to destroy VM")
            return web.json_response({'status': 'Failed'}, status=500)
        else:
            return web.json_response({'status': 'Success'}, status=200)


if __name__ == '__main__':
    CloudResourceManager()
