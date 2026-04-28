output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.gym.id
}

output "public_ip" {
  description = "Elastic IP address of the EC2 instance"
  value       = aws_eip.gym.public_ip
}

output "public_dns" {
  description = "Public DNS hostname of the EC2 instance"
  value       = aws_instance.gym.public_dns
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket used for experiment storage"
  value       = aws_s3_bucket.gym_data.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.gym_data.arn
}

output "backend_url" {
  description = "URL for the FastAPI backend"
  value       = "http://${aws_eip.gym.public_ip}:8000"
}

output "frontend_url" {
  description = "URL for the React frontend"
  value       = "http://${aws_eip.gym.public_ip}"
}
