from tabpfn.model_configs import get_base_config
import lightning as L
import torch
import pytest

from tabpfn.priors import ClassificationAdapterPrior, MLPPrior
from tabpfn.priors.utils import uniform_int_sampler_f
from tabpfn.priors.flexible_categorical import ClassificationAdapter
from tabpfn.priors.differentiable_prior import parse_distributions

@pytest.mark.parametrize("num_features", [11, 51])
@pytest.mark.parametrize("batch_size", [4, 8])
@pytest.mark.parametrize("n_classes", [2, 4])
@pytest.mark.parametrize("n_samples", [128, 900])
def test_classification_prior(batch_size, num_features, n_samples, n_classes):
    # test the mlp prior
    L.seed_everything(42)
    prior = ClassificationAdapterPrior(MLPPrior())
    hyperparameters = {
        'prior_mlp_activations': lambda: torch.nn.ReLU, # relu is callable so we'd try to call it thinking it's a sampling function....
        'is_causal' : False,
        'num_causes': 3, # actually ignored because is_causal is False
        'prior_mlp_hidden_dim': 128,
        'num_layers': 3,
        'noise_std': 0.1,
        'y_is_effect': True,
        'pre_sample_weights': False,
        'prior_mlp_dropout_prob': 0.1,
        'block_wise_dropout': True,
        'init_std': 0.1,
        'sort_features': False,
        'in_clique': False,
        'pre_sample_causes': True,
        'n_samples_used': n_samples,
        'num_classes': n_classes,
        'num_features_used': num_features,
        'balanced': False,
        'multiclass_type': 'rank',
        'output_multiclass_ordered_p': 0,
        'verbose': True,
        'prior_mlp_scale_weights_sqrt': True,
        'random_feature_rotation': True,
        'add_uninformative_features': False,
        'nan_prob_no_reason': 0,
        'nan_prob_a_reason': 0,
        'nan_prob_unknown_reason': 0,
        'categorical_feature_p': 0.2,

    }
    x, y, y_ = prior.get_batch(batch_size=batch_size, num_features=num_features, n_samples=n_samples, device='cpu', hyperparameters=hyperparameters)
    assert x.shape == (n_samples, batch_size, num_features)
    assert y.shape == (n_samples, batch_size)
    assert y_.shape == (n_samples, batch_size)
    # because of the strange sampling, we an have less than n_classes many classes.
    assert y_.max() < n_classes
    assert y_.min() == 0
    if n_samples == 128 and batch_size == 4 and num_features == 11 and n_classes == 2:
        assert float(x[0, 0, 0])== -0.46619218587875366
        assert float(y[0, 0]) == 1.0


def test_classification_adapter_with_sampling():
    batch_size = 16
    num_features = 100
    n_samples = 900
    # test the mlp prior
    L.seed_everything(42)
    hyperparameters = {
        'is_causal' : False,
        'prior_mlp_activations': {'distribution': 'meta_choice_mixed', 'choice_values': [
            torch.nn.Tanh, torch.nn.Identity, torch.nn.ReLU
        ]},
        'is_causal' : False,
        'num_causes': {'distribution': 'meta_gamma', 'max_alpha': 3, 'max_scale': 7, 'round': True,
                       'lower_bound': 2}, # actually ignored because is_causal is False
        'prior_mlp_hidden_dim': {'distribution': 'meta_gamma', 'max_alpha': 3, 'max_scale': 100, 'round': True, 'lower_bound': 4},
        'num_layers': {'distribution': 'meta_gamma', 'max_alpha': 2, 'max_scale': 3, 'round': True,
                       'lower_bound': 2},
        'noise_std': 0.1,
        'y_is_effect': True,
        'pre_sample_weights': False,
        'prior_mlp_dropout_prob': {'distribution': 'meta_beta', 'scale': 0.6, 'min': 0.1, 'max': 5.0},        'noise_std': 0.1,
        'block_wise_dropout': True,
        'init_std': 0.1,
        'sort_features': False,
        'in_clique': False,
        'n_samples_used': n_samples,
        'balanced': False,
        'multiclass_type': 'rank',
        'output_multiclass_ordered_p': 0,
        'verbose': True,
        'prior_mlp_scale_weights_sqrt': True,
        'random_feature_rotation': True,
        'add_uninformative_features': False,
        'pre_sample_causes': True,
        'nan_prob_no_reason': 0,
        'nan_prob_a_reason': 0,
        'nan_prob_unknown_reason': 0,
        'categorical_feature_p': 0.2,
        "num_classes": uniform_int_sampler_f(2, 10),
        "num_features_used": uniform_int_sampler_f(1, 100)
    }
    hyperparameters = parse_distributions(hyperparameters)
    mlp_config = dict(prior_mlp_scale_weights_sqrt=hyperparameters['prior_mlp_scale_weights_sqrt'], random_feature_rotation=hyperparameters['random_feature_rotation'],
                                                              pre_sample_causes=hyperparameters['pre_sample_causes'], add_uninformative_features=hyperparameters['add_uninformative_features'])
    adapter = ClassificationAdapter(MLPPrior(mlp_config), hyperparameters, config={})
    assert adapter.h['num_layers'] == 6
    assert adapter.h['num_features_used'] == 7
    assert adapter.h['num_classes'] == 3

    args = {'device': 'cpu', 'n_samples': n_samples, 'num_features': num_features}
    x, y, y_ = adapter(batch_size=batch_size, **args)
    assert x.shape == (n_samples, batch_size, num_features)
    assert y.shape == (n_samples, batch_size)
    assert y_.shape == (n_samples, batch_size)

    assert float(x[0, 0, 0]) == pytest.approx(-18.84649658203125)
    assert float(y[0, 0]) == 1.0
