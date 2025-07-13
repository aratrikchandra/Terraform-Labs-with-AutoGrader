
# EC2 details
resource "aws_instance" "example-ec2" {
  ami           = var.ami_id_value
  instance_type = var.instance_type_value
  vpc_security_group_ids = [aws_security_group.TF_SG.id]
  user_data     =  "${file("install_apache.sh")}"
  
  tags = {
    Name = "example-ec2"
  }
}

#security group details

resource "aws_security_group" "TF_SG" {
  name        = "security group using Terraform"
  description = "security group using Terraform"
  vpc_id      = var.vpc_id_value

  ingress {
    description      = "HTTP"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "TF_SG"
  }
}