# Output variables
output "vpc_id" {
  value = aws_vpc.example_vpc.id
}

output "public_subnet_id" {
  value = aws_subnet.public_subnet.id
}

output "private_subnet_id" {
  value = aws_subnet.private_subnet.id
}

output "igw_id" {
  value = aws_internet_gateway.my_igw.id
}

output "route_table_id" {
  value = aws_route_table.public_rt.id
}