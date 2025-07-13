output "public-ip-address" {
  description = "Public IP address of the EC2 instance"
  value = aws_instance.example-ec2.public_ip
}

output "instance_id" {
  description = "The ID of the EC2 instance"
  value       = aws_instance.example-ec2.id
}

output "securitygroup" {
  description = "Security group ID"
  value = aws_security_group.TF_SG.id
}