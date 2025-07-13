import json
import os
import subprocess
import time
import boto3

def verify_terraform_setup():
    terraform_outputs = {
        "status": "failure"
    }
    try:
        state_file_path = "terraform.tfstate"
        if not os.path.exists(state_file_path):
            raise FileNotFoundError("Terraform state file not found.")

        with open(state_file_path, 'r') as f:
            terraform_state = json.load(f)

        outputs = terraform_state.get('outputs', {})
        required_keys = ["vpc_id", "public_subnet_1_id", "public_subnet_2_id", "igw_id", "route_table_id", "security_group_id", "eks_cluster_id", "eks_cluster_endpoint", "eks_node_group_id", "kubectl_server_instance_id"]

        if all(key in outputs for key in required_keys):
            terraform_outputs = {
                "vpc_id": outputs["vpc_id"]["value"],
                "public_subnet_1_id": outputs["public_subnet_1_id"]["value"],
                "public_subnet_2_id": outputs["public_subnet_2_id"]["value"],
                "igw_id": outputs["igw_id"]["value"],
                "route_table_id": outputs["route_table_id"]["value"],
                "security_group_id": outputs["security_group_id"]["value"],
                "eks_cluster_id": outputs["eks_cluster_id"]["value"],
                "eks_cluster_endpoint": outputs["eks_cluster_endpoint"]["value"],
                "eks_node_group_id": outputs["eks_node_group_id"]["value"],
                "kubectl_server_instance_id": outputs["kubectl_server_instance_id"]["value"],
                "status": "success"
            }

    except subprocess.CalledProcessError as e:
        print(f"Terraform command failed: {e}")
    except Exception as e:
        print(f"An error occurred during Terraform setup: {e}")

    return terraform_outputs

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
        if vpc["CidrBlock"] == expected_cidr:
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
        elif subnet['CidrBlock'] != expected_cidr:
            result["message"] = "Public subnet CIDR block does not match the expected value."
        elif subnet['AvailabilityZone'] != expected_az:
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

def verify_security_group(security_group_id, expected_vpc_id, ec2_client, data):
    result = {
        "testid": "Security Group Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }

    try:
        response = ec2_client.describe_security_groups(GroupIds=[security_group_id])
        security_group = response['SecurityGroups'][0]

        if security_group['VpcId'] != expected_vpc_id:
            result['message'] = "Security group VPC ID does not match the expected value."
        else:
            ingress_rules = security_group['IpPermissions']
            egress_rules = security_group['IpPermissionsEgress']

            if not any(rule['FromPort'] == 80 and rule['ToPort'] == 80 and '0.0.0.0/0' in [ip['CidrIp'] for ip in rule['IpRanges']] for rule in ingress_rules):
                result['message'] = "Ingress rules do not match the expected configuration."
            elif not any(rule['IpProtocol'] == '-1' and '0.0.0.0/0' in [ip['CidrIp'] for ip in rule['IpRanges']] for rule in egress_rules):
                result['message'] = "Egress rules do not match the expected configuration."
            else:
                result['status'] = "success"
                result['score'] = 1
                result['message'] = "Security group matches the expected configuration."

    except Exception as e:
        result['message'] = f"An error occurred: {e}"

    data.append(result)


def verify_eks_cluster(eks_cluster_id, expected_vpc_id, expected_subnet_ids, eks_client, data):
    result = {
        "testid": "EKS Cluster Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    
    try:
        response = eks_client.describe_cluster(name=eks_cluster_id)
        cluster = response['cluster']
        
        # Verify basic configuration
        if cluster['name'] != "pc-eks":
            result["message"] = "Cluster name does not match expected value 'pc-eks'"
        elif cluster['resourcesVpcConfig']['vpcId'] != expected_vpc_id:
            result["message"] = "Cluster VPC ID does not match expected VPC"
        elif set(cluster['resourcesVpcConfig']['subnetIds']) != set(expected_subnet_ids):
            result["message"] = "Cluster subnet IDs do not match expected subnets"
        elif not cluster['resourcesVpcConfig']['endpointPublicAccess']:
            result["message"] = "Public endpoint access not enabled"
        else:
            result["status"] = "success"
            result["score"] = 1
            result["message"] = "EKS cluster configuration is correct"

    except Exception as e:
        result["message"] = f"Error verifying EKS cluster: {str(e)}"
    
    data.append(result)

def verify_kubectl_server(instance_id, expected_subnet_id, expected_sg_id, ec2_client, data):
    result = {
        "testid": "Kubectl Server Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        # Verify instance configuration
        if instance['InstanceType'] != "t2.micro":
            result["message"] = "Invalid instance type for kubectl server"
        elif instance['SubnetId'] != expected_subnet_id:
            result["message"] = "Kubectl server deployed in wrong subnet"
        elif expected_sg_id not in [sg['GroupId'] for sg in instance['SecurityGroups']]:
            result["message"] = "Kubectl server missing required security group"
        elif instance['ImageId'] != "ami-063e1495af50e6fd5":
            result["message"] = "Incorrect AMI used for kubectl server"
        else:
            result["status"] = "success"
            result["score"] = 1
            result["message"] = "Kubectl server configuration is correct"

    except Exception as e:
        result["message"] = f"Error verifying kubectl server: {str(e)}"
    
    data.append(result)

def verify_node_group(node_group_name, cluster_name, expected_instance_type, expected_subnets, eks_client, data):
    result = {
        "testid": "Node Group Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    
    try:
        response = eks_client.describe_nodegroup(
            clusterName=cluster_name,
            nodegroupName=node_group_name
        )
        ng = response['nodegroup']
        
        # Verify node group configuration
        if ng['instanceTypes'][0] != expected_instance_type:
            result["message"] = f"Instance type mismatch. Expected {expected_instance_type}"
        elif ng['scalingConfig']['desiredSize'] != 2:
            result["message"] = "Desired node count not set to 2"
        elif ng['scalingConfig']['minSize'] != 1:
            result["message"] = "Minimum node count not set to 1"
        elif ng['scalingConfig']['maxSize'] != 3:
            result["message"] = "Maximum node count not set to 3"
        elif set(ng['subnets']) != set(expected_subnets):
            result["message"] = "Node group subnets do not match expected subnets"
        elif ng['labels'].get('env') != "dev":
            result["message"] = "Missing or incorrect node group labels"
        else:
            result["status"] = "success"
            result["score"] = 1
            result["message"] = "Node group configuration is correct"

    except Exception as e:
        result["message"] = f"Error verifying node group: {str(e)}"
    
    data.append(result)

def verify_cluster_functionality(data):
    result = {
        "testid": "Cluster Functionality",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    
    try:
        # Update kubeconfig
        subprocess.run(
            ["aws", "eks", "update-kubeconfig", "--region", "ap-southeast-1", "--name", "pc-eks"],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Verify node readiness
        nodes = subprocess.check_output(
            ["kubectl", "get", "nodes", "-o", "json"],
            stderr=subprocess.STDOUT,
            text=True
        )
        node_data = json.loads(nodes)
        ready_nodes = sum(1 for node in node_data["items"] if 
            any(c["type"] == "Ready" and c["status"] == "True" 
                for c in node["status"]["conditions"]))
        
        if ready_nodes < 2:
            result["message"] = f"Only {ready_nodes}/2 nodes ready"
            data.append(result)
            return
        result["status"] = "success"
        result["score"] = 1
        result["message"] = "Cluster fully operational - nodes ready and application accessible"

    except subprocess.CalledProcessError as e:
        result["message"] = f"Command failed: {e.output}"
    except Exception as e:
        result["message"] = f"Unexpected error: {str(e)}"
    
    data.append(result)
def main():
    # labDirectoryPath = "/home/labDirectory/"
    labDirectoryPath = ""

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
    default_security_group = {
        "testid": "Security Group Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. Security Group verification skipped."
    }
    default_eks_cluster = {
        "testid": "EKS Cluster Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. EKS Cluster verification skipped."
    }
    default_kubectl_server = {
        "testid": "Kubectl Server Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. Kubectl Server verification skipped."
    }
    default_node_group = {
        "testid": "Node Group Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. Node Group verification skipped."
    }
    default_cluster_functionality = {
        "testid": "Cluster Functionality",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": "Terraform setup failed. Cluster Functionality verification skipped."
    }
    overall = {"data": []}
    data = []
    terraform_outputs = verify_terraform_setup()
    if terraform_outputs["status"] == "success":
        vpc_id = terraform_outputs["vpc_id"]
        public_subnet_1_id = terraform_outputs["public_subnet_1_id"]
        public_subnet_2_id = terraform_outputs["public_subnet_2_id"]
        igw_id = terraform_outputs["igw_id"]
        route_table_id = terraform_outputs["route_table_id"]
        security_group_id = terraform_outputs["security_group_id"]
        eks_cluster_id = terraform_outputs["eks_cluster_id"]
        eks_node_group_id = terraform_outputs["eks_node_group_id"]
        kubectl_server_instance_id = terraform_outputs["kubectl_server_instance_id"]



        vpc_cidr_block = "10.0.0.0/16"
        public_subnet_1_cidr_block = "10.0.1.0/24"
        public_subnet_2_cidr_block = "10.0.2.0/24"
        availability_zone_1 = "ap-southeast-1a"
        availability_zone_2 = "ap-southeast-1b"

        ec2_client = boto3.client(
            'ec2',
            region_name= "ap-southeast-1"
        )

                # Fetch all route tables
        route_tables = ec2_client.describe_route_tables()["RouteTables"]

        flag = verify_vpc(vpc_id, ec2_client, vpc_cidr_block, data)
        if flag:
            verify_public_subnet(public_subnet_1_id, public_subnet_1_cidr_block, availability_zone_1, ec2_client, vpc_id, igw_id, route_tables,data)
            verify_public_subnet(public_subnet_2_id, public_subnet_2_cidr_block, availability_zone_2, ec2_client, vpc_id, igw_id, route_tables,data)
            verify_internet_gateway(igw_id, vpc_id, ec2_client, data)
            verify_route_table(route_table_id, vpc_id, igw_id, ec2_client, data)
            verify_security_group(security_group_id, vpc_id,ec2_client, data)

            # New verifications
            eks_client = boto3.client('eks', region_name="ap-southeast-1")
            
            # Verify EKS Cluster
            expected_subnet_ids = [public_subnet_1_id, public_subnet_2_id]
            verify_eks_cluster(
                eks_cluster_id=eks_cluster_id,
                expected_vpc_id=vpc_id,
                expected_subnet_ids=expected_subnet_ids,
                eks_client=eks_client,
                data=data
            )
            
            # Verify Kubectl Server
            verify_kubectl_server(
                instance_id=kubectl_server_instance_id,
                expected_subnet_id=public_subnet_1_id,
                expected_sg_id=security_group_id,
                ec2_client=ec2_client,
                data=data
            )
            
            # Verify Node Group
            verify_node_group(
                node_group_name="pc-node-group",
                cluster_name="pc-eks",
                expected_instance_type="t2.small",
                expected_subnets=expected_subnet_ids,
                eks_client=eks_client,
                data=data
            )
            verify_cluster_functionality(data)
        else:
            default_public_subnet["message"] = "VPC verification failed. Public Subnet verification skipped."
            default_igw["message"] = "VPC verification failed. Internet Gateway verification skipped."
            default_route_table["message"] = "VPC verification failed. Route Table verification skipped."
            default_security_group["message"] = "VPC verification failed. Security Group verification skipped."
            default_eks_cluster["message"] = "VPC verification failed. Kube cluster verification skipped."
            default_kubectl_server["message"] = "VPC verification failed. Kube cluster verification skipped."
            default_node_group["message"] = "VPC verification failed. Node Group verification skipped."
            default_cluster_functionality["message"] = "VPC verification failed. Cluster Functionality Check skipped."
            data.append(default_public_subnet)
            data.append(default_public_subnet)
            data.append(default_igw)
            data.append(default_route_table)
            data.append(default_security_group)
            data.append(default_eks_cluster)
            data.append(default_kubectl_server)
            data.append(default_node_group)
            data.append(default_cluster_functionality)

    else:
        data.append(default_vpc)
        data.append(default_public_subnet)
        data.append(default_public_subnet)
        data.append(default_igw)
        data.append(default_route_table)
        data.append(default_security_group)
        data.append(default_eks_cluster)
        data.append(default_kubectl_server)
        data.append(default_node_group)
        data.append(default_cluster_functionality)
    
    overall['data'] = data
    with open(os.path.join(labDirectoryPath, '../evaluate.json'), 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    main()
