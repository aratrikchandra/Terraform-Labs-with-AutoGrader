FROM ubuntu:22.04 as ubuntu-stage

# Installing common packages
RUN apt-get update -y && apt-get install -y software-properties-common language-pack-en-base debconf-utils curl
RUN apt-get update -y && apt-get install -y net-tools wget nano vim less gnupg
RUN apt-get update -y && apt-get install -y iproute2 python3 python3-pip

# Install additional utilities
RUN apt-get install -y man-db zip

# Upgrade pip and install Python packages
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install boto3 requests

# Setup Environment variables
ENV INSTRUCTOR_SCRIPTS="/home/.evaluationScripts"
ENV LAB_DIRECTORY="/home/labDirectory"
ENV PATH="/home/.evaluationScripts:${PATH}"
ENV TERM=xterm-256color

# Create directory structure
RUN mkdir -p /home/labDirectory && mkdir -p /home/.evaluationScripts

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl.sha256" \
    && echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl kubectl.sha256

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws

# Install Terraform
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update && apt-get install -y terraform \
    && rm -rf /var/lib/apt/lists/*

# Configure shell environment
RUN echo "cd /home/labDirectory" > /root/.bashrc \
    && echo "alias ls='ls --color=always'" >> /root/.bashrc \
    && echo "rm -f \`find /home -type f -name \"._*\"\`" >> /root/.bashrc

# Copy application files
# COPY labDirectory /home/labDirectory
# COPY .evaluationScripts /home/.evaluationScripts

# Set working directory
# WORKDIR /home

CMD [ "/bin/bash", "-c", "while :; do sleep 10; done" ]