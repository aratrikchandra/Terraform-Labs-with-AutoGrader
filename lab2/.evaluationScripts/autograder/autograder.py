import json
import os
import subprocess
import time
import boto3

def verify_terraform_setup(data):
    result = {
        "testid": "Terraform Setup Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    terraform_outputs = {
        "status": "failure"
    }
    tfvars = {}
    try:
        subprocess.run(["terraform", "init"], check=True)
        
        subprocess.run(["terraform", "destroy", "-auto-approve"], check=True)
        
        subprocess.run(["terraform", "apply", "-auto-approve"], check=True)

        state_file_path = "terraform.tfstate"
        if not os.path.exists(state_file_path):
            raise FileNotFoundError("Terraform state file not found.")

        with open(state_file_path, 'r') as f:
            terraform_state = json.load(f)

        outputs = terraform_state.get('outputs', {})
        required_keys = ["vpc_id", "public_subnet_id", "private_subnet_id", "igw_id", "route_table_id"]

        if all(key in outputs for key in required_keys):
            terraform_outputs = {
                "vpc_id": outputs["vpc_id"]["value"],
                "public_subnet_id": outputs["public_subnet_id"]["value"],
                "private_subnet_id": outputs["private_subnet_id"]["value"],
                "igw_id": outputs["igw_id"]["value"],
                "route_table_id": outputs["route_table_id"]["value"],
                "status" : "failure"
            }

            # Load expected values from terraform.tfvars
            with open("terraform.tfvars", 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        tfvars[key.strip()] = value.strip().strip('"')
            required_keys = ["vpc_cidr_block", "public_subnet_cidr_block", "private_subnet_cidr_block", "availability_zone", "access_key_value", "secret_key_value", "region_value"]
            if all(key in tfvars for key in required_keys):
                result["status"] = "success"
                result["score"] = 1
                result["message"] = "Terraform setup completed successfully."
                terraform_outputs["status"] = "success"
            else:
                result["message"] = "Terraform input variables are incomplete or missing required keys."
        else:
            result["message"] = "Terraform outputs are incomplete or missing required keys."

    except subprocess.CalledProcessError as e:
        result["message"] = f"Terraform command failed: {e}"
    except Exception as e:
        result["message"] = f"An error occurred during Terraform setup: {e}"

    data.append(result)
    return terraform_outputs, tfvars

def verify_vpc(vpc_id, ec2_client, expected_cidr, data):
    result = {
        "testid": "VPC Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        vpc = ec2_client.describe_vpcs(VpcIds=[vpc_id])["Vpcs"][0]
        if vpc["CidrBlock"] == "10.0.0.0/16" and vpc["CidrBlock"] == expected_cidr:
            result["status"] = "success"
            result["score"] = 1
            result["message"] = "VPC configuration is correct."
            data.append(result)
            return True
        else:
            result["message"] = "VPC CIDR block does not match expected value."
    except Exception as e:
        result["message"] = f"Error verifying VPC: {e}"
    data.append(result)
    return False

def verify_public_subnet(subnet_id, expected_cidr, expected_az, ec2_client, vpc_id, igw_id, route_tables, data):
    result = {
        "testid": "Public Subnet Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }

    try:
        response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
        subnet = response['Subnets'][0]

        if subnet['VpcId'] != vpc_id:
            result["message"] = "Public subnet does not belong to the expected VPC."
        elif subnet['CidrBlock'] != expected_cidr or subnet['CidrBlock'] != "10.0.1.0/24":
            result["message"] = "Public subnet CIDR block does not match the expected value."
        elif subnet['AvailabilityZone'] != expected_az or subnet['AvailabilityZone'] != "us-east-1b":
            result["message"] = "Public subnet Availability Zone does not match the expected value."
        else:
            # Check if the subnet is associated with a route table having IGW route
            associated_route_table = None
            for route_table in route_tables:
                for association in route_table['Associations']:
                    if association.get('SubnetId') == subnet_id:
                        associated_route_table = route_table
                        break

            if not associated_route_table:
                result["message"] = "Public subnet is not associated with any route table."
            else:
                # Check if there is a route to the Internet Gateway
                has_igw_route = any(
                    route.get('DestinationCidrBlock') == '0.0.0.0/0' and 
                    route.get('GatewayId') == igw_id 
                    for route in associated_route_table['Routes']
                )

                if has_igw_route:
                    result["status"] = "success"
                    result["score"] = 1
                    result["message"] = "Public subnet is correctly configured."
                else:
                    result["message"] = "Public subnet does not have a route to the Internet Gateway."

    except Exception as e:
        result["message"] = f"An error occurred: {e}"

    data.append(result)

def verify_private_subnet(subnet_id, expected_cidr, expected_az, ec2_client, vpc_id, igw_id, route_tables, data):
    result = {
        "testid": "Private Subnet Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }

    try:
        response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
        subnet = response['Subnets'][0]

        if subnet['VpcId'] != vpc_id:
            result["message"] = "Private subnet does not belong to the expected VPC."
        elif subnet['CidrBlock'] != expected_cidr or subnet['CidrBlock'] != "10.0.2.0/24":
            result["message"] = "Private subnet CIDR block does not match the expected value."
        elif subnet['AvailabilityZone'] != expected_az or subnet['AvailabilityZone'] != "us-east-1b":
            result["message"] = "Private subnet Availability Zone does not match the expected value."
        else:
            # Check if the subnet is associated with a route table
            associated_route_table = None
            for route_table in route_tables:
                for association in route_table['Associations']:
                    if association.get('SubnetId') == subnet_id:
                        associated_route_table = route_table
                        break

            if not associated_route_table:
                result["status"] = "success"
                result["score"] = 1
                result["message"] = "Private subnet is correctly configured."
            else:
                # Check if the subnet does NOT have a route to the Internet Gateway
                has_igw_route = any(
                    route.get('DestinationCidrBlock') == '0.0.0.0/0' and 
                    route.get('GatewayId') == igw_id 
                    for route in associated_route_table['Routes']
                )

                if has_igw_route:
                    result["message"] = "Private subnet incorrectly has a route to the Internet Gateway."
                else:
                    result["status"] = "success"
                    result["score"] = 1
                    result["message"] = "Private subnet is correctly configured."

    except Exception as e:
        result["message"] = f"An error occurred: {e}"

    data.append(result)

def verify_internet_gateway(igw_id, vpc_id, ec2_client, data):
    result = {
        "testid": "Internet Gateway Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        igw = ec2_client.describe_internet_gateways(InternetGatewayIds=[igw_id])["InternetGateways"][0]
        attached = any(attachment["VpcId"] == vpc_id for attachment in igw["Attachments"])
        if attached:
            result["status"] = "success"
            result["score"] = 1
            result["message"] = "Internet Gateway is attached to the correct VPC."
        else:
            result["message"] = "Internet Gateway is not correctly attached."
    except Exception as e:
        result["message"] = f"Error verifying Internet Gateway: {e}"
    data.append(result)

def verify_route_table(route_table_id, expected_vpc_id, expected_igw_id, ec2_client, data):
    result = {
        "testid": "Route Table Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }

    try:
        response = ec2_client.describe_route_tables(RouteTableIds=[route_table_id])
        route_table = response['RouteTables'][0]

        if route_table['VpcId'] != expected_vpc_id:
            result["message"] = "Route table does not belong to the expected VPC."
        else:
            # Check if a route exists for internet access via the IGW
            has_igw_route = any(
                route.get('DestinationCidrBlock') == '0.0.0.0/0' and 
                route.get('GatewayId') == expected_igw_id 
                for route in route_table['Routes']
            )

            if has_igw_route:
                result["status"] = "success"
                result["score"] = 1
                result["message"] = "Route table is correctly configured with an Internet Gateway route."
            else:
                result["message"] = "Route table does not have a correct route to the Internet Gateway."

    except Exception as e:
        result["message"] = f"An error occurred: {e}"

    data.append(result)



def main():
    # labDirectoryPath = "/home/labDirectory/"

    default_vpc = {
        "testid": "VPC Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. VPC verification skipped."
    }
    default_public_subnet = {
        "testid": "Public Subnet Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. Public Subnet verification skipped."
    }
    default_private_subnet = {
        "testid": "Private Subnet Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. Private Subnet verification skipped."
    }
    default_igw = {
        "testid": "Internet Gateway Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. Internet Gateway verification skipped."
    }
    default_route_table = {
        "testid": "Route Table Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. Route Table verification skipped."
    }
    
    overall = {"data": []}
    data = []
    terraform_result, tfvars = verify_terraform_setup(data)
    if terraform_result["status"] == "success":
        vpc_id = terraform_result["vpc_id"]
        public_subnet_id = terraform_result["public_subnet_id"]
        private_subnet_id = terraform_result["private_subnet_id"]
        igw_id = terraform_result["igw_id"]
        route_table_id = terraform_result["route_table_id"]


        vpc_cidr_block = tfvars.get('vpc_cidr_block')
        public_subnet_cidr_block = tfvars.get('public_subnet_cidr_block')
        private_subnet_cidr_block = tfvars.get('private_subnet_cidr_block')
        availability_zone = tfvars.get('availability_zone')

        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=tfvars.get("access_key_value"),
            aws_secret_access_key=tfvars.get("secret_key_value"),
            region_name=tfvars.get("region_value")
        )

                # Fetch all route tables
        route_tables = ec2_client.describe_route_tables()["RouteTables"]

        flag = verify_vpc(vpc_id, ec2_client, vpc_cidr_block, data)
        if flag:
            verify_public_subnet(public_subnet_id, public_subnet_cidr_block, availability_zone, ec2_client, vpc_id, igw_id, route_tables,data)
            verify_private_subnet(private_subnet_id, private_subnet_cidr_block, availability_zone, ec2_client, vpc_id, igw_id, route_tables,data)
            verify_internet_gateway(igw_id, vpc_id, ec2_client, data)
            verify_route_table(route_table_id, vpc_id, igw_id, ec2_client, data)
        else:
            default_public_subnet["message"] = "VPC verification failed. Public Subnet verification skipped."
            default_private_subnet["message"] = "VPC verification failed. Private Subnet verification skipped."
            default_igw["message"] = "VPC verification failed. Internet Gateway verification skipped."
            default_route_table["message"] = "VPC verification failed. Route Table verification skipped."
            data.append(default_public_subnet)
            data.append(default_private_subnet)
            data.append(default_igw)
            data.append(default_route_table)

    else:
        data.append(default_vpc)
        data.append(default_public_subnet)
        data.append(default_private_subnet)
        data.append(default_igw)
        data.append(default_route_table)
    
    overall['data'] = data
    with open('../evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    main()
