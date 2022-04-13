# allow importing from one directory up
import sys
sys.path.append('..')

import shap
import modisco
import wandb
import numpy as np
import tensorflow as tf

import models
import dataset
import utils


# TODO convert constants to config settings
NUM_BG = 20
NUM_FG = 5
MODEL_PATH = "/home/csestili/repos/mouse_sst/wandb/run-20220408_112918-eg1rb9tq/files/model-best.h5"
POS_LABEL = 1

def explain():
    init()
    bg, fg = get_data(NUM_BG, NUM_FG)
    shap_values = get_deepshap_scores(MODEL_PATH, bg, fg)
    modisco_results = get_modisco_results(shap_values, fg)
    return modisco_results

def init():
	config, project = utils.get_config("../config-mouse-sst.yaml")
	wandb.init(config=config, project=project, mode="disabled")
	utils.validate_config(wandb.config)

def get_data(num_bg, num_fg):
	train_data = dataset.FastaTfDataset(wandb.config.train_data_paths, wandb.config.train_labels)
	val_data = dataset.FastaTfDataset(wandb.config.val_data_paths, wandb.config.val_labels)

	bg = np.array([itm[0] for itm in train_data.ds.take(num_bg).as_numpy_iterator()])
	fg = np.array([itm[0] for itm in val_data.ds.take(num_fg).as_numpy_iterator()])

	return bg, fg

def get_deepshap_scores(model_path, bg, fg):
	model = models.load_model(model_path)
	explainer = shap.DeepExplainer(model, bg)
	shap_values = explainer.shap_values(fg)

	return shap_values

class ModiscoNormalization:
	VALID_NORMALIZATION_TYPES = ['none', 'gkm_explain', 'pointwise']

	def __init__(self, normalization_type):
		normalization_type = normalization_type.lower()
		if normalization_type not in self.VALID_NORMALIZATION_TYPES:
			raise ValueError(f"Invalid normalization type. Allowed values are {self.VALID_NORMALIZATION_TYPES}, got {normalization_type}")
		self.normalization_type = normalization_type

	def __call__(self, hyp_impscores, sequences):
		"""
		Args:
			hyp_impscores [num_sequences, seq_len, 4]: hypothetical importance scores
			sequences [num_sequences, seq_len, 4]: 1-hot encoded actual sequences

		Returns:
			normed_impscores [num_sequences, seq_len, 4]
			normed_hyp_impscores [num_sequences, seq_len, 4]
		"""
		if self.normalization_type == 'none':
			return self.identity_normalization(hyp_impscores, sequences)
		elif self.normalization_type == 'gkm_explain':
			return self.gkm_explain_normalization(hyp_impscores, sequences)
		elif self.normalization_type == 'pointwise':
			return self.pointwise_normalization(hyp_impscores, sequences)
		else:
			raise NotImplementedError(self.normalization_type)

	@staticmethod
	def identity_normalization(hyp_impscores, sequences):
		normed_hyp_impscores = hyp_impscores
		normed_impscores = normed_hyp_impscores * sequences
		return normed_impscores, normed_hyp_impscores

	@staticmethod
	def gkm_explain_normalization(hyp_impscores, sequences):
		# implements equations (27) and (28) from A.3 of GkmExplain supplementary material
		# https://academic.oup.com/bioinformatics/article/35/14/i173/5529147#supplementary-data

		# actual_scores is f_h(S_x, i, S_x^i)
		actual_scores = np.sum(hyp_impscores * sequences, axis=-1)[:, np.newaxis]
		numerator = hyp_impscores * actual_scores
		denominator = np.sum(hyp_impscores * (hyp_impscores * actual_scores > 0), axis=-1)[:, np.newaxis]
		normed_hyp_impscores = numerator / denominator
		normed_impscores = normed_hyp_impscores * sequences
		return normed_impscores, normed_hyp_impscores

	@staticmethod
	def pointwise_normalization(hyp_impscores, sequences):
		# adapted from https://github.com/kundajelab/tfmodisco/blob/master/examples/H1ESC_Nanog_gkmsvm/TF%20MoDISco%20Nanog.ipynb
		# TODO vectorize
		normed_hyp_impscores = np.array([x - np.mean(x, axis=-1)[:,None] for x in hyp_impscores])
		normed_impscores = normed_hyp_impscores * sequences
		return normed_impscores, normed_hyp_impscores

def _test_gkm_explain_normalization():
	hyp_impscores = np.array([[1, -2, 3, -4], [-5, 6, -7, 8], [-9, 1, 2, -3]])
	sequences     = np.array([[0,  1, 0,  0], [ 0, 0,  0, 1], [ 1, 0, 0,  0]])

	numerator     = np.array([[-2, 4, -6, 8], [-40, 48, -56, 64], [81, -9, -18, 27]])
	# TODO denominator sum parts

	# TODO actually test

def get_modisco_results(shap_values, fg):
	hyp_imp_scores = shap_values[POS_LABEL]
	normalization = ModiscoNormalization('pointwise')
	normed_impscores, normed_hyp_impscores = normalization(hyp_imp_scores, fg)

	seqlets_to_patterns_factory = modisco.tfmodisco_workflow.seqlets_to_patterns.TfModiscoSeqletsToPatternsFactory(
        trim_to_window_size=11,
        initial_flank_to_add=3,
        final_flank_to_add=3,
        kmer_len=7, num_gaps=1,
        num_mismatches=1)
	workflow = modisco.tfmodisco_workflow.workflow.TfModiscoWorkflow(
        sliding_window_size=11,
        flank_size=3,
        seqlets_to_patterns_factory=seqlets_to_patterns_factory)
	tfmodisco_results = workflow(
	                task_names=["task0"],
	                contrib_scores={'task0': normed_impscores},
	                hypothetical_contribs={'task0': normed_hyp_impscores},
	                one_hot=fg)

	return tfmodisco_results


if __name__ == '__main__':
	explain()