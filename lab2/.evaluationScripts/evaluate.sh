#! /bin/bash

# For Testing
INSTRUCTOR_SCRIPTS="/home/.evaluationScripts"
# INSTRUCTOR_SCRIPTS="."
LAB_DIRECTORY="../labDirectory"


ptcd=$(pwd)

cd $INSTRUCTOR_SCRIPTS
# echo $ptcd

list_of_files="$(ls $LAB_DIRECTORY)"


cp -r $LAB_DIRECTORY/* autograder/

cd ./autograder/

chmod -R 777 $list_of_files

./grader.sh

# Run terraform destroy to clean up resources
terraform destroy -auto-approve

rm -r $list_of_files

if [ -d .terraform ]; then
    rm -rf .terraform
fi


# Check and remove Terraform-related files
if [ -f terraform.tfstate ]; then
    rm terraform.tfstate
fi

if [ -f terraform.tfstate.backup ]; then
    rm terraform.tfstate.backup
fi

if [ -f .terraform.lock.hcl ]; then
    rm .terraform.lock.hcl
fi


cd "$ptcd"