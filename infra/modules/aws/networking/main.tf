resource "aws_vpc" "cloud-waste-hunter" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = var.tags
}

resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.cloud-waste-hunter.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = var.tags
}

resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.cloud-waste-hunter.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = var.tags
}

resource "aws_internet_gateway" "cloud-waste-hunter" {
  vpc_id = aws_vpc.cloud-waste-hunter.id
  tags = var.tags
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.cloud-waste-hunter.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.cloud-waste-hunter.id
  }
}

resource "aws_route_table_association" "public" {
  count          = length(var.public_subnet_cidrs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Simple NAT Gateway setup
resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "cloud-waste-hunter" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.cloud-waste-hunter]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.cloud-waste-hunter.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.cloud-waste-hunter.id
  }
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnet_cidrs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

output "vpc_id" {
  value = aws_vpc.cloud-waste-hunter.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}
