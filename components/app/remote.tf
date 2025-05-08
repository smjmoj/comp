
data "terraform_remote_state" "bastion" {
  backend = "s3"
  config = {
    key = "bastion/terraform.tfstate"
  }
}
