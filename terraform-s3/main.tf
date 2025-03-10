provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "cloud_assignment_bucket" {
  bucket = "cloud-assignment-bucket-1710"
}

resource "aws_s3_object" "example_file" {
      bucket = aws_s3_bucket.cloud_assignment_bucket.id
      key    = "uploaded-file.py"
      source = "./hello.py"
      acl    = "private"
    }
