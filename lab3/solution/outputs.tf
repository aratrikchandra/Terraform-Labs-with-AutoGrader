# outputs.tf

# VPC Details
output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

# Subnet Details
output "public_subnet_1_id" {
  description = "The ID of the first public subnet"
  value       = aws_subnet.public-1.id
}

output "public_subnet_2_id" {
  description = "The ID of the second public subnet"
  value       = aws_subnet.public-2.id
}

# Internet Gateway Details
output "igw_id" {
  description = "The ID of the Internet Gateway"
  value       = aws_internet_gateway.gw.id
}

output "route_table_id" {
  value = aws_route_table.rtb.id
}
# Security Group Details
output "security_group_id" {
  description = "The ID of the security group"
  value       = aws_security_group.allow_http.id
}

# EKS Cluster Details
output "eks_cluster_id" {
  description = "The ID of the EKS cluster"
  value       = aws_eks_cluster.eks.id
}


output "eks_cluster_endpoint" {
  description = "The endpoint for the EKS cluster"
  value       = aws_eks_cluster.eks.endpoint
}

# EKS Node Group Details
output "eks_node_group_id" {
  description = "The id of the EKS node group"
  value       = aws_eks_node_group.node-grp.id
}

output "kubectl_server_instance_id" {
  description = "The instance ID of the kubectl server"
  value       = aws_instance.kubectl-server.id
}