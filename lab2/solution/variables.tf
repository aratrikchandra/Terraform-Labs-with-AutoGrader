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

variable "vpc_cidr_block" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "public_subnet_cidr_block" {
  description = "CIDR block for the public subnet"
  type        = string
}

variable "private_subnet_cidr_block" {
  description = "CIDR block for the private subnet"
  type        = string
}

variable "availability_zone" {
  description = "The availability zone to use for subnets"
  type        = string
}
