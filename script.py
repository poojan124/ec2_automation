'''
The following script will create server on AWS (EC2). Based on server config given in command line argument.
Requirements:
    - boto3, yaml python package.
    - boto3 config set in environment. (https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-environment-variables)
        - Need to setup AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
'''

import boto3
import yaml
import sys

if len(sys.argv) < 2:
    print("Please provide config file name.")
    sys.exit(1)

config_file = sys.argv[1]
session = boto3.Session(region_name='us-east-2')
ec2 = session.client(service_name='ec2')

with open(config_file, 'r') as f:
    yaml_file = f.read()

yaml_config = yaml.load(yaml_file, Loader=yaml.FullLoader)

user_name = yaml_config['users'][0]['login']

# Following block of code will create shell script to run at start of VM initialization
# It will mount drive to location given in cofig with given file system type

shell_cmd_base = """sudo mkfs -t {0} /dev/nvme{1}n1 && sudo mkdir -p {2} && sudo mount /dev/nvme{1}n1 {2}"""
shell_script = "#!/bin/bash \n"

volumes = yaml_config['volumes']
block_device_mapping = []

for i, vol in enumerate(volumes):

    device = dict()
    device['DeviceName'] = vol['device']
    device['VirtualName'] = vol['device']
    device['Ebs'] = {
        'VolumeSize': vol['size_gb'],
        'VolumeType': 'gp2'
    }
    block_device_mapping.append(device)
    shell_script += shell_cmd_base.format(vol['type'], i+1, vol['mount'])
    shell_script += '\n'

# create security group required to connect to server (ssh port 22)

sec_grp = ec2.create_security_group(Description='ec2 ssh {0}'.format(user_name),GroupName='ec2_ssh_{0}'.format(user_name))
sec_res = ec2.authorize_security_group_ingress(
    GroupId=sec_grp['GroupId'],
    FromPort=22,
    ToPort=22,
    CidrIp='0.0.0.0/0',
    IpProtocol='tcp'
)

# import key pair
key_res = ec2.import_key_pair(KeyName=user_name, PublicKeyMaterial=yaml_config['users'][0]['ssh_key'].encode())

# create ec2 instance
ec2_res = ec2.run_instances(
    InstanceType=yaml_config['instance_type'],
    BlockDeviceMappings=block_device_mapping,
    ImageId = 'ami-013de1b045799b282',
    MinCount = 1,
    MaxCount = 1,
    KeyName=user_name,
    UserData=shell_script
)