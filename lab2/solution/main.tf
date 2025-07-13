# 1. Create a VPC
resource "aws_vpc" "example_vpc" {
  cidr_block = var.vpc_cidr_block
  tags = {
    Name = "examples_vpc"
  }
}

# 2. Create a public subnet
resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.example_vpc.id
  availability_zone       = var.availability_zone
  cidr_block              = var.public_subnet_cidr_block
  map_public_ip_on_launch = true
  tags = {
    Name = "PublicSubnet"
  }
}

# 3. Create a private subnet
resource "aws_subnet" "private_subnet" {
  vpc_id                  = aws_vpc.example_vpc.id
  availability_zone       = var.availability_zone
  cidr_block              = var.private_subnet_cidr_block
  map_public_ip_on_launch = false
  tags = {
    Name = "PrivateSubnet"
  }
}

# 4. Create an Internet Gateway (IGW)
resource "aws_internet_gateway" "my_igw" {
  vpc_id = aws_vpc.example_vpc.id
  tags = {
    Name = "IGW"
  }
}

# 5. Create a route table for the public subnet
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.example_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.my_igw.id
  }

  tags = {
    Name = "PublicRouteTable"
  }
}

# 6. Associate the public route table with the public subnet
resource "aws_route_table_association" "public_rt_association" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}
