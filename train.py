"""train.py: Train a model.

Usage:
- Single training run, from interactive session: python train.py -config config-base.yaml
- Single training run, on slurm: sbatch train.sb config-base.yaml
- Hyperparameter sweep, on slurm: see README.md
"""

import callbacks
import dataset
import models
import lr_schedules
import utils

import wandb
from wandb.keras import WandbCallback


def train(args):
	# Start `wandb`
	config, project = utils.get_config(args.config)
	wandb.init(config=config, project=project, mode=args.wandb_mode)
	utils.validate_config(wandb.config)

	# Get datasets
	train_data = dataset.SequenceTfDataset(
		wandb.config.train_data_paths, wandb.config.train_labels,
		targets_are_classes=True, endless=True,
		batch_size=wandb.config.batch_size)
	val_data = dataset.SequenceTfDataset(
		wandb.config.val_data_paths, wandb.config.val_labels,
		targets_are_classes=True,
		endless=not wandb.config.use_exact_val_metrics,
		batch_size=wandb.config.batch_size)

	# Get model
	batch_size, steps_per_epoch_train, steps_per_epoch_val = utils.get_step_size(
		wandb.config, train_data, val_data)
	lr_schedule = lr_schedules.get_lr_schedule(steps_per_epoch_train, wandb.config)
	model = models.get_model(
		train_data.fc.seq_shape, train_data.fc.num_classes, lr_schedule, wandb.config)

	# Get callbacks
	callback_fns = callbacks.get_early_stopping_callbacks(wandb.config)
	callback_fns.extend([WandbCallback(), callbacks.LRLogger(model.optimizer)])

	# Train
	model.fit(
		train_data.dataset,
		epochs=wandb.config.num_epochs,
		steps_per_epoch=steps_per_epoch_train,
		validation_data=val_data.dataset,
		validation_steps=steps_per_epoch_val,
		callbacks=callback_fns)

def validate(model_path):
	"""Run trained model on full validation set."""
	model = models.load_model(model_path)
	val_data = dataset.SequenceTfDataset(
		wandb.config.val_data_paths, wandb.config.val_labels,
		targets_are_classes=True, endless=False)
	model.evaluate(val_data.ds.batch(wandb.config.batch_size))

def get_args():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('-config', type=str, required=True)
	parser.add_argument('-wandb-mode', type=str)
	# parse_known_args() allows hyperparameters to be passed in during sweeps
	args, _ = parser.parse_known_args()
	return args


if __name__ == '__main__':
	train(get_args())
