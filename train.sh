#!/bin/bash
#
# Usage: bash train.sh <path to config>

# Activate environment
source activate /ocean/projects/bio200034p/csestili/02319-hw-cnn/env/keras2-tf27

# Check environment variables
if [[ -z $PARTITION_GPU ]]
then
    echo "Error: \$PARTITION_GPU is not set."
    exit 1
fi

# Check arguments
config_path=$1

if [ -z $config_path ];
then
    echo "Error: Missing arguments"
    echo "Usage: bash train.sh <path to config>"
    exit 1
fi

sbatch -p $PARTITION_GPU -t 08:00:00 scripts/train_main.sb $config_path
