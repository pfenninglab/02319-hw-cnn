# CNN Training Platform

## About
This tool enables you to train a CNN model on DNA sequences.
Classification (2 or more classes) and regression (single variable) are both supported.

Specify datasets, targets, CNN architecture, hyperparameters, and training details
from a text configuration file.

Track experiments, visualize performance metrics, and search hyperparameters using
the `wandb` framework.

## Setup

1. Start an interactive session:

```
srun -n 1 -p RM-shared --pty bash
```

2. Clone the repo. It is recommended that you clone into a directory just for repositories:

```
mkdir ~/repos
cd ~/repos
git clone https://github.com/pfenninglab/02319-hw-cnn.git
```

3. Install Miniconda:
```
bash /ocean/projects/ibn200014p/csestili/02319-hw-cnn/install/Miniconda3-latest-Linux-x86_64.sh
```

4. Change conda settings, and restart the interactive session:
```
conda init bash
exit
srun -n 1 -p RM-shared --pty bash
```

5. Test conda environment:
```
conda activate /ocean/projects/ibn200014p/csestili/02319-hw-cnn/env/keras2-tf27
```
Note: This is a shared conda environment for the whole class. This was created to save everyone time installing packages. Usually when you use conda, you create and manage your own environments.

6. Create a `wandb` account: [signup link](https://app.wandb.ai/login?signup=true)
 
 NOTE: `wandb` account usernames cannot be changed. I recommend creating a username like
 `<name>-cmu`, e.g. `csestili-cmu`, in case you want to have different accounts for personal
 use or for other future workplaces.

During account creation, you will be asked if you want to create a team. You do not need to do this.

7. Log in to `wandb` on the PSC:
```
conda activate /ocean/projects/ibn200014p/csestili/02319-hw-cnn/env/keras2-tf27
wandb login
```

8. Once you have logged in to `wandb`, you can leave the interactive session and return to the head node:
```
exit
```

## Model training

### Single training run
To train a single model:

1. Edit `config-base.yaml` to configure:
- `wandb` project name for tracking
- data sources
- targets
- CNN architecture
- regularization
- learning rate and optimizer
- training details
- SHAP details

For example training config files, see `config-classification.yaml` and `config-regression.yaml` in the `example_configs/` directory.

2. Start training:
```
bash train.sh config-base.yaml
```

3. Check experiment results in-browser at [https://wandb.ai/](https://wandb.ai/).

Trained models are saved in the `wandb/` directory.

### Hyperparameter sweep
To initiate a hyperparameter sweep, training many models with different hyperparameters:

1. Edit `config-base.yaml` as above, for all the parameters that should remain **fixed** during training.

2. Edit `sweep-config.yaml`, specifying all the parameters that should **vary** during the search, as well as the ranges to search over.

If you saved your copy of `config-base.yaml` under a different name in step 1, be sure to change the base config name in the `command` section of `sweep-config.yaml`.

3. Start the sweep:
```
bash start_sweep.sh sweep-config.yaml
```
This will output a sweep id, e.g. `<your wandb id>/<project name>/kztk7ceb`. Copy it for the next step.

4. Start the sweep agents in parallel:
```
bash start_agents.sh <num_agents> <throttle> <sweep_id>
```
where
- `<num_agents>` is the total number of agents you want to run in the sweep.
- `<throttle>` is the maximum number of agents to run simultaneously. It is recommended to set this to `4` or less. Please use this to keep resources free for other users!
- `<sweep_id>` is the sweep id you got in step 3.

5. Check sweep results in-browser at [https://wandb.ai/](https://wandb.ai/).

Trained models are saved in the `wandb/` directory.

## Using a trained model

### Finding a trained model

When you train a model, the training run gets an associated run ID.
The trained model is saved in a directory called `wandb/run-<date_string>-<run_id>`.

To find the directory associated with a given run:
1. Go to that run in the `wandb` user interface, e.g. https://wandb.ai/<wandb username>/02319-hw-cnn/runs/1gimqghi .
2. The run ID is the part of that URL after `runs/`. E.g. for the above model, the run id is `1gimqghi`.
3. On the PSC, find the trained model with this run id. You can use the `find` command for this:
```
find wandb/ -wholename *<run id>*/files/model-final.h5
```

Note: The asterisks are part of the command. E.g. for the above model, you would use 
`find wandb/ -wholename *1gimqghi*/files/model-final.h5`.

This will give you a path to the trained model.

To get the final model, use `model-final.h5`.
To get the model with the lowest validation loss, use `model-best.h5`.

### Get activations from a trained model

You can get the activations from a trained model, either at the output layer or at an intermediate layer, using `scripts/get_activations.py`:
```
cd ~/repos/02319-hw-cnn/scripts/ # (this repo's scripts/ folder)
srun -p GPU-shared -n 1 --gres gpu:1 --pty bash
conda activate /ocean/projects/ibn200014p/csestili/02319-hw-cnn/env/keras2-tf27

python get_activations.py \
  -model <path to model .h5>
  -in_file <path to input .fa, .bed, or .narrowPeak file> \
  [-in_genome <path to genome .fa file, if in_file is .bed or .narrowPeak>] \
  -out_file <path to output file, .npy or .csv> \
  [-layer_name <layer name to get activations from, e.g. 'flatten'>. default is output layer] \
  [--no_reverse_complement, don't evaluate on reverse complement sequences] \
  [--write_csv, write activations as .csv file instead of .npy] \
  [-score_column <output unit to extract score in the csv, e.g. 1>. default writes whole activation as a row]
```
To get a numpy array of activations from an intermediate layer:
```
  -layer_name <layer_name>
  [don't pass --write_csv]
```
To get a csv of probabilities for the positive class from a binary classifier:
```
  [don't pass -layer_name]
  --write_csv
  -score_column 1
```

**NOTE:** By default, reverse complement sequences are included. The output file will have twice as many activations as the input file has sequences. The order of results is:
```
pred(example_1)
pred(revcomp(example_1))
...
pred(example_n)
pred(revcomp(example_n))
```
To exclude reverse complement sequences, pass `--no_reverse_complement`.

