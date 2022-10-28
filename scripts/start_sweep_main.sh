#!/bin/bash

# If training env isn't already activated, then activate it
if [ "$CONDA_DEFAULT_ENV" != "/ocean/projects/bio200034p/csestili/02319-hw-cnn/env/keras2-tf27" ]; then
	source activate /ocean/projects/bio200034p/csestili/02319-hw-cnn/env/keras2-tf27
fi

wandb login
wandb sweep $1
