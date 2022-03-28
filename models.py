
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.regularizers import l2
from tensorflow.keras.optimizers import SGD, Adam
from tensorflow.keras.metrics import SparseCategoricalAccuracy

from metrics import MulticlassAUC


CONFIG = {
	'num_conv_layers': 2,
	'conv_filters': 300,
	'conv_width': 7,
	'conv_stride': 1,
    'dropout_rate': 0.3,
    'max_pool_size': 26,
    'max_pool_stride': 26,
    'dense_filters': 300,
    'l2_reg': 1e-4,
    'lr_init': 1e-3,
    'lr_max': 1e-1,
    'optimizer': 'adam'
}
OPTIMIZER_MAPPING = {
	'sgd': SGD,
	'adam': Adam
}


def get_model(input_shape, num_classes, lr_schedule, config):
	inputs = keras.Input(shape=input_shape)
	x = inputs
	
	for _ in range(config['num_conv_layers']):
		x = layers.Conv1D(filters=config['conv_filters'], kernel_size=config['conv_width'], activation='relu', strides=config['conv_stride'], kernel_regularizer=l2(l=config['l2_reg']))(x)
		x = layers.Dropout(rate=config['dropout_rate'])(x)

	x = layers.MaxPooling1D(pool_size=config['max_pool_size'], strides=config['max_pool_stride'])(x)
	x = layers.Flatten()(x)
	x = layers.Dense(units=config['dense_filters'], activation='relu', kernel_regularizer=l2(l=config['l2_reg']))(x)
	x = layers.Dropout(rate=config['dropout_rate'])(x)

	outputs = layers.Dense(num_classes, activation="softmax", kernel_regularizer=l2(l=config['l2_reg']))(x)

	model = keras.Model(inputs=inputs, outputs=outputs)
	optimizer = OPTIMIZER_MAPPING[config['optimizer'].lower()](learning_rate=lr_schedule)
	model.compile(loss='sparse_categorical_crossentropy',
		optimizer=optimizer,
		metrics=[SparseCategoricalAccuracy(),
			MulticlassAUC(name='auroc', pos_label=1, curve='ROC'),
			MulticlassAUC(name='auprc', pos_label=1, curve='PR')])

	return model
