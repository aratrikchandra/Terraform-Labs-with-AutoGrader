FROM ubuntu:22.04 as ubuntu-stage

# Installing common packages
RUN yes | unminimize
RUN apt-get update -y && apt-get install -y software-properties-common language-pack-en-base debconf-utils curl
RUN apt-get update -y && apt-get install net-tools wget nano vim less gnupg -y
RUN apt-get update -y && apt-get install iproute2 python3 python3-pip -y

# Install anything you want here:
RUN apt-get install -y man-db
RUN apt-get install -y zip

# Upgrade pip and install boto3
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install boto3 requests

# Setup Environment variables
ENV INSTRUCTOR_SCRIPTS="/home/.evaluationScripts"
ENV LAB_DIRECTORY="/home/labDirectory"
ENV PATH="/home/.evaluationScripts:${PATH}"
ENV TERM=xterm-256color

# Setup Directory Structure
RUN mkdir /home/labDirectory
RUN mkdir /home/.evaluationScripts

# Add HashiCorp GPG key and repository
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list

# Install Terraform
RUN apt-get update && \
    apt-get install -y terraform && \
    rm -rf /var/lib/apt/lists/*

# Global Settings
RUN echo "cd /home/labDirectory" > /root/.bashrc
RUN echo "alias ls='ls --color=always'" >> /root/.bashrc
RUN echo "rm -f \`find /home -type f -name \"._*\"\`" >> /root/.bashrc

# Copy directories to the container
# COPY labDirectory /home/labDirectory
# COPY .evaluationScripts /home/.evaluationScripts

# # Set the working directory
# WORKDIR /home

CMD [ "/bin/bash", "-c", "while :; do sleep 10; done" ]