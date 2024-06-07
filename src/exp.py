import argparse
import slune
import os
import matplotlib.pyplot as plt
from train import pretrain, train
import numpy as np
import torch
from xgb import get_xgb
from nn import get_nn
from utils import get_data, get_X_y_labelled, check_preprocessed

# If running labelled_exp
def labelled_exp(saver, **config):
    check_preprocessed()
    # Get and prepare the data
    train_data, test_data, validate_data = get_data()
    X_train, y_train = get_X_y_labelled(train_data)
    # X_val, y_val = get_X_y_labelled(validate_data) Not currently using validation data
    X_test, y_test = get_X_y_labelled(test_data)

    X_train = X_train.to_numpy()
    y_train = y_train.to_numpy()
    X_test = X_test.to_numpy()
    y_test = y_test.to_numpy()

    # Get the model
    if config['model'] == 'xgboost':
        model = get_xgb(lr=config['learning_rate'])
    elif config['model'] == 'neural_net':
        model = get_nn(
            lr=config['learning_rate'], 
            opt=config['opt'], 
            loss=config['loss'], 
            num_epochs=config['num_epochs'], 
            batch_size=config['batch_size'],
            update_ratio=config['update_ratio'],
            num_update_epochs=config['num_update_epochs'],
            MLP_shape=config['MLP_shape'],
            )
    else:
        raise ValueError("Model not recognized.")
    
    # Train the model
    metrics = pretrain(model, X_train, y_train, X_test, y_test)

    # Save results
    saver.log(metrics)
    saver.save_collated()

    # If we are using cuda we clear the memory
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return metrics

# If running missing_labels_exp
def missing_labels_exp(saver, **config):
    raise NotImplementedError("Missing labels experiment not implemented yet.")

# Following will be run on the cluster as a job, after being queued by run.py
if  __name__ == "__main__":
    # Parse input from command line
    parser = argparse.ArgumentParser()
    parser.add_argument('--benchmark', type=str, help='Name of the benchmark to use', default="labelled_exp")
    parser.add_argument('--model', type=str, help='Model to use', default="xgb")
    parser.add_argument('--learning_rate', type=float, help='Learning rate to use', default=0.01)
    parser.add_argument('--num_epochs', type=int, help='Number of epochs to train for', default=200)
    parser.add_argument('--batch_size', type=str, help='Batch size to use', default='max')
    parser.add_argument('--opt', type=str, help='Optimizer to use', default="adam")
    parser.add_argument('--loss', type=str, help='Loss function to use', default="logloss")
    parser.add_argument('--update_ratio', type=float, help='Ratio of update epochs to training epochs', default=0.1)
    parser.add_argument('--num_update_epochs', type=int, help='Number of update epochs to run', default=10)
    parser.add_argument('--MLP_shape', type=str, help='Shape of the MLP', default="128,128")
    parser.add_argument('--query_method', type=str, help='Query method to use', default="")
    parser.add_argument('--query_K', type=int, help='Number of samples to query', default=10)
    parser.add_argument('--query_alpha', type=float, help='Alpha for query method', default=0.1)
    parser.add_argument('--query_args', type=str, help='Additional arguments for query method', default="")

    args = parser.parse_args()

    config = {
        'benchmark': args.benchmark,
        'model': args.model,
        'num_epochs': args.num_epochs,
        'batch_size': args.batch_size,
        'opt': args.opt,
        'loss': args.loss,
        'update_ratio': args.update_ratio,
        'num_update_epochs': args.num_update_epochs,
        'MLP_shape': args.MLP_shape,
        'query_method': args.query_method,
        'query_K': args.query_K,
        'query_alpha': args.query_alpha,
        'query_args': args.query_args,
    }

    to_grid ={
        'learning_rate': [0.1, 0.01, 0.001, 0.0001],
    }
    print("Constants: ", config, flush=True)
    print("Searching Over: ", to_grid, flush=True)
    grid = slune.searchers.SearcherGrid(to_grid, runs=1)
    grid.check_existing_runs(slune.get_csv_saver(root_dir='results'))
    for g in grid:
        # Add the net to the config
        g = slune.utils.ls_to_dict(g)
        config = {**config, **g}
        saver = slune.get_csv_saver(root_dir='results', params=config)
        # Train the model
        if config['benchmark'] == 'labelled_exp':
            metrics = labelled_exp(saver, **config)
        elif config['benchmark'] == 'missing_labels':
            metrics = missing_labels_exp(saver, **config)
        else:
            raise ValueError("Benchmark not recognized.")
        # Create path for saving
        path = os.path.dirname(saver.get_path(slune.utils.dict_to_ls(**config)))
        print("path: ", path, flush=True)
        
        # Produce and save plots
        # if config['benchmark'] == 'labelled_exp':
        #     plot_labelled_exp(metrics, path)
        # elif config['benchmark'] == 'missing_labels':
        #     plot_missing_labels(metrics, path)
        # TODO: Implement plotting functions

        # Clear GPU memory
        torch.cuda.empty_cache()