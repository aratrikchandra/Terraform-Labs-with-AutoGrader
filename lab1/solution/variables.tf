# Credential
variable "access_key_value" {
  description = "Acess key ID of the IAM user"
}

variable "secret_key_value" {
  description = "Secret Acess Key of the IAM user"
}

variable "region_value" {
  description = "AWS Region"
}

# EC2
variable "ami_id_value" {
  description = "The AMI ID for the EC2 instance"
  type        = string
}

variable "instance_type_value" {
  description = "The type of instance to create"
  type        = string
}

# Security Group
variable "vpc_id_value" {
  description = "VPC ID for the Security Group"
}