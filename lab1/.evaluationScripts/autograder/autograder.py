import json
import os
import subprocess
import time
import boto3
import requests

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
        # Initialize and apply Terraform
        subprocess.run(["terraform", "init"], check=True)

        # Destroy any existing Terraform infrastructure
        subprocess.run(["terraform", "destroy", "-auto-approve"], check=True)

        subprocess.run(["terraform", "apply", "-auto-approve"], check=True)

        # Parse the Terraform state file
        state_file_path = "terraform.tfstate"
        if not os.path.exists(state_file_path):
            raise FileNotFoundError("Terraform state file not found.")

        with open(state_file_path, 'r') as f:
            terraform_state = json.load(f)

        outputs = terraform_state.get('outputs', {})
        required_keys = ["instance_id", "public-ip-address", "securitygroup"]

        # Verify required outputs exist
        if all(key in outputs for key in required_keys):
            result["status"] = "success"
            result["score"] = 1
            result["message"] = "Terraform setup completed successfully, and outputs are valid."
            terraform_outputs = {
                "instance_id": outputs["instance_id"]["value"],
                "public_ip": outputs["public-ip-address"]["value"],
                "security_group_id": outputs["securitygroup"]["value"],
                "status": "failure"
            }

            # Load expected values from terraform.tfvars
            with open("terraform.tfvars", 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        tfvars[key.strip()] = value.strip().strip('"')
            required_keys = ["vpc_id_value", "instance_type_value", "ami_id_value", "access_key_value", "secret_key_value", "region_value"]
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


def verify_ec2_instance(instance_id, public_ip, expected_security_id, expected_ami_id, expected_instance_type, ec2_client, data):
    result = {
        "testid": "EC2 Instance Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }

    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        security_groups = instance['SecurityGroups']
        security_group_ids = [sg['GroupId'] for sg in security_groups]

        if instance['State']['Name'] != 'running':
            result['message'] = "EC2 instance is not running."
            data.append(result)
            return
        # Check if the security group ID matches the expected security ID
        if expected_security_id not in security_group_ids:
            result['message'] = "Security group ID does not match the expected Security Group ID. "
            data.append(result)
            return
        # Check if the AMI ID matches the expected AMI ID
        if instance['ImageId'] != expected_ami_id:
            result['message'] = "AMI ID does not match the expected AMI ID. "
            data.append(result)
            return
        # Check if the instance type matches the expected instance type
        if instance['InstanceType'] != expected_instance_type or instance['InstanceType'] != "t2.micro":
            result['message'] = "Instance type does not match the expected instance type. "
            data.append(result)
            return

        result['message'] = "EC2 instance matches the expected specifications."
        
        # Retry mechanism to verify the application is running
        max_retries = 10
        wait_time = 3
        for attempt in range(max_retries):
            time.sleep(wait_time)
            response = requests.get(f"http://{public_ip}")
            if response.status_code == 200 and "Welcome : Apache installed" in response.text:
                result['status'] = 'success'
                result['score'] = 1
                result['message'] += " Application is accessible and running correctly."
                break
                
        if result['status'] != 'success':
            result['message'] += "Application did not become accessible within the allowed retries."

    except Exception as e:
        result['message'] = f"An error occurred: {e}"

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

def main():
    # labDirectoryPath = "/home/labDirectory/"
    labDirectoryPath = ""
    overall = {"data": []}
    data = []

# Step 1: Verify Terraform setup
    terraform_result, tfvars = verify_terraform_setup(data)
    terraform_success = terraform_result["status"] == "success"

    if terraform_success:
        # Step 2: Extract Terraform outputs
        instance_id = terraform_result["instance_id"]
        public_ip = terraform_result["public_ip"]
        security_group_id = terraform_result["security_group_id"]

        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=tfvars.get("access_key_value"),
            aws_secret_access_key=tfvars.get("secret_key_value"),
            region_name=tfvars.get("region_value")
        )
        # Step 4: Verify security group
        verify_security_group(security_group_id, tfvars.get("vpc_id_value"), ec2_client, data)

        # Step 5: Verify EC2 instance
        verify_ec2_instance(instance_id, public_ip, security_group_id , tfvars.get("ami_id_value"), tfvars.get("instance_type_value"), ec2_client, data)

    else:
        # Log skipped EC2 and security group checks if Terraform failed
        data.append({
            "testid": "Security Group Verification",
            "status": "failure",
            "score": 0,
            "maximum marks": 1,
            "message": "Terraform setup failed. Security Group verification skipped."
        })
        data.append({
            "testid": "EC2 Verification",
            "status": "failure",
            "score": 0,
            "maximum marks": 1,
            "message": "Terraform setup failed. EC2 verification skipped."
        })


    # Save the result to evaluate.json
    overall['data'] = data
    with open('../evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    main()
