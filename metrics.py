import tensorflow as tf
import tensorflow.keras.metrics


class MulticlassAUC(tensorflow.keras.metrics.AUC):
    # adapted from https://stackoverflow.com/a/63604257
    def __init__(self, pos_label, from_logits=False, sparse=True, **kwargs):
        super().__init__(**kwargs)

        self.pos_label = pos_label
        self.from_logits = from_logits
        self.sparse = sparse

    def update_state(self, y_true, y_pred, **kwargs):
        """Accumulates confusion matrix statistics.

        Parameters
        ----------
        y_true : tf.Tensor
            The ground truth values. Either an integer tensor of shape
            (n_examples,) (if sparse=True) or a one-hot tensor of shape
            (n_examples, n_classes) (if sparse=False).

        y_pred : tf.Tensor
            The predicted values, a tensor of shape (n_examples, n_classes).

        **kwargs : keyword arguments
            Extra keyword arguments for the metric's update_state() method.
        """
        if self.sparse:
            y_true = tf.math.equal(y_true, self.pos_label)
            y_true = tf.squeeze(y_true)
        else:
            y_true = y_true[..., self.pos_label]

        if self.from_logits:
            y_pred = tf.nn.softmax(y_pred, axis=-1)
        y_pred = y_pred[..., self.pos_label]

        super().update_state(y_true, y_pred, **kwargs)

    def get_config(self):
        config = super().get_config()
        config.update({
            "pos_label": self.pos_label,
            "from_logits": self.from_logits,
            "sparse": self.sparse
        })
        return config

class MulticlassMetric(tensorflow.keras.metrics.Metric):
    """Binary metric for a multiclass problem, by treating one label as positive and the rest as negative.
    adapted from https://stackoverflow.com/a/63604257

    This implementation allows you to plug in any binary Keras metric.

    Args:
        k_metric_name (str): Keras metric class name as a string.
        pos_label : int
            Label of the positive class (the one whose metric is being computed).

        from_logits : bool, optional (default: False)
            If True, assume predictions are not standardized to be between 0 and 1.
            In this case, predictions will be squeezed into probabilities using the
            softmax function.

        sparse : bool, optional (default: True)
            If True, ground truth labels should be encoded as integer indices in the
            range [0, n_classes-1]. Otherwise, ground truth labels should be one-hot
            encoded indicator vectors (with a 1 in the true label position and 0
            elsewhere).

        **kwargs : keyword arguments
            Keyword arguments to be passed to Keras metric.

    """
    def __init__(self, k_metric_name, pos_label, from_logits=False, sparse=True, **kwargs):
        super().__init__(name=kwargs['name'])
        self.k_metric_name = k_metric_name
        self.k_metric = self._get_k_metric(**kwargs)
        self.pos_label = pos_label
        self.from_logits = from_logits
        self.sparse = sparse

    def update_state(self, y_true, y_pred, **kwargs):
        """Accumulates confusion matrix statistics.

        Parameters
        ----------
        y_true : tf.Tensor
            The ground truth values. Either an integer tensor of shape
            (n_examples,) (if sparse=True) or a one-hot tensor of shape
            (n_examples, n_classes) (if sparse=False).

        y_pred : tf.Tensor
            The predicted values, a tensor of shape (n_examples, n_classes).

        **kwargs : keyword arguments
            Extra keyword arguments for the metric's update_state() method.
        """
        if self.sparse:
            y_true = tf.math.equal(y_true, self.pos_label)
            y_true = tf.squeeze(y_true)
        else:
            y_true = y_true[..., self.pos_label]

        if self.from_logits:
            y_pred = tf.nn.softmax(y_pred, axis=-1)
        y_pred = y_pred[..., self.pos_label]

        self.k_metric.update_state(y_true, y_pred, **kwargs)

    def result(self):
        return self.k_metric.result()

    def reset_state(self):
        self.k_metric.reset_state()

    def get_config(self):
        """For model saving and loading"""
        config = self.k_metric.get_config()
        config.update({
            "k_metric_name": self.k_metric_name,
            "pos_label": self.pos_label,
            "from_logits": self.from_logits,
            "sparse": self.sparse
        })
        return config

    def _get_k_metric(self, **kwargs):
        # Try to get metric as keras builtin metric
        k_metric = getattr(tensorflow.keras.metrics, self.k_metric_name, None)
        if k_metric is None:
            # Try to get metric as custom metric from this module
            current_module = __import__(__name__)
            k_metric = getattr(current_module, self.k_metric_name, None)

        if k_metric is None:
            raise ValueError(f"Could not find keras metric {self.k_metric_name}")
        return k_metric(**kwargs)

class Specificity(tensorflow.keras.metrics.Metric):
    def __init__(self, **kwargs):
        super(Specificity, self).__init__(**kwargs)

        self.tn = self.add_weight(name='tn', initializer='zeros')
        self.fp = self.add_weight(name='fp', initializer='zeros')

    def update_state(self, y_true, y_pred, sample_weight=None):
        y_true = tf.cast(y_true, tf.bool)
        y_pred = tf.cast(y_pred, tf.bool)

        batch_tn = tf.logical_and(tf.equal(y_true, False), tf.equal(y_pred, False))
        batch_tn = tf.cast(batch_tn, self.dtype)
        if sample_weight is not None:
            sample_weight = tf.cast(sample_weight, self.dtype)
            sample_weight = tf.broadcast_to(sample_weight, batch_tn.shape)
            batch_tn = tf.multiply(batch_tn, sample_weight)
        self.tn.assign_add(tf.reduce_sum(batch_tn))

        batch_fp = tf.logical_and(tf.equal(y_true, False), tf.equal(y_pred, True))
        batch_fp = tf.cast(batch_fp, self.dtype)
        if sample_weight is not None:
            sample_weight = tf.cast(sample_weight, self.dtype)
            sample_weight = tf.broadcast_to(sample_weight, batch_fp.shape)
            batch_fp = tf.multiply(batch_fp, sample_weight)
        self.fp.assign_add(tf.reduce_sum(batch_fp))

        return self.tn

    def result(self):
        return self.tn / (self.tn + self.fp)

    def reset_state(self):
        self.tn.assign(0)
        self.fp.assign(0)

class MultiClassSpecificity(tensorflow.keras.metrics.Metric):
    pass
