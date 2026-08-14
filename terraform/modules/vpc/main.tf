resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "veyor-vpc-${var.environment}"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "veyor-igw-${var.environment}"
  }
}

# Public Subnets (For ALBs and NAT Gateways)
resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name                                           = "veyor-public-subnet-${count.index + 1}-${var.environment}"
    "kubernetes.io/role/elb"                       = "1" # Tells AWS ALB Controller this is for Public Load Balancers
    "kubernetes.io/cluster/veyor-eks-${var.environment}" = "shared"
  }
}

# Private Subnets (For EKS Worker Nodes & RDS)
resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name                                           = "veyor-private-subnet-${count.index + 1}-${var.environment}"
    "kubernetes.io/role/internal-elb"              = "1" # Tells AWS ALB Controller this is for Internal Load Balancers
    "kubernetes.io/cluster/veyor-eks-${var.environment}" = "shared"
  }
}

# Elastic IP for NAT
resource "aws_eip" "nat" {
  count  = var.single_nat_gateway ? 1 : length(var.public_subnet_cidrs)
  domain = "vpc"

  tags = {
    Name = "veyor-nat-eip-${count.index + 1}-${var.environment}"
  }
}

# NAT Gateway (Provides outbound internet to private worker pods)
resource "aws_nat_gateway" "main" {
  count         = var.single_nat_gateway ? 1 : length(var.public_subnet_cidrs)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "veyor-nat-gw-${count.index + 1}-${var.environment}"
  }
}

# Route Table for Private Subnets
resource "aws_route_table" "private" {
  count  = length(var.private_subnet_cidrs)
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = var.single_nat_gateway ? aws_nat_gateway.main[0].id : aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name = "veyor-private-rt-${count.index + 1}-${var.environment}"
  }
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnet_cidrs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}