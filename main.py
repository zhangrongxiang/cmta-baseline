import os
import sys

import csv
import time
import numpy as np

from datasets.dataset_survival import Generic_MIL_Survival_Dataset
from utils.options import parse_args
from utils.util import get_split_loader, set_seed

from utils.loss import define_loss
from utils.optimizer import define_optimizer
from utils.scheduler import define_scheduler


class FlushFile:
    def __init__(self, f):
        self.f = f

    def write(self, x):
        self.f.write(x)
        self.f.flush()

    def flush(self):
        self.f.flush()


def main(args):
    # set random seed for reproduction
    set_seed(args.seed)

    # create results directory
    results_dir = "./results/{dataset}/[{model}]-[{fusion}]-[{alpha}]-[{time}]-[{modality}]".format(
        dataset=args.dataset,
        model=args.model,
        fusion=args.fusion,
        alpha=args.alpha,
        time=time.strftime("%Y-%m-%d]-[%H-%M-%S"),
        modality=args.modal,
    )
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    log_file = os.path.join(results_dir, '___logging.txt')
    log_file_handle = open(log_file, 'w')
    sys.stdout = FlushFile(log_file_handle)
    # 5-fold cross validation
    header = ["folds", "fold 0", "fold 1", "fold 2", "fold 3", "fold 4", "mean", "std"]
    best_epoch = ["best epoch"]
    best_score = ["best cindex"]

    print("=======================================")
    print("所有参数：", vars(args))
    print("=======================================")

    # start 5-fold CV evaluation.
    for fold in range(5):
        # build dataset
        dataset = Generic_MIL_Survival_Dataset(
            csv_path="./csv/%s_all_clean.csv" % (args.dataset),
            modal=args.modal,
            OOM=args.OOM,
            apply_sig=True,
            data_dir=args.data_root_dir,
            shuffle=False,
            seed=args.seed,
            patient_strat=False,
            n_bins=4,
            label_col="survival_months",
        )
        split_dir = os.path.join("./splits", args.which_splits, args.dataset)
        train_dataset, val_dataset = dataset.return_splits(
            from_id=False, csv_path="{}/splits_{}.csv".format(split_dir, fold)
        )
        train_loader = get_split_loader(
            train_dataset,
            training=True,
            weighted=args.weighted_sample,
            modal=args.modal,
            batch_size=args.batch_size,
        )
        val_loader = get_split_loader(
            val_dataset, modal=args.modal, batch_size=args.batch_size
        )
        print(
            "training: {}, validation: {}".format(len(train_dataset), len(val_dataset))
        )

        # build model, criterion, optimizer, schedular
        if args.model == "cmta":
            from models.cmta.network import CMTA
            from models.cmta.engine import Engine

            print(train_dataset.omic_sizes)
            model_dict = {
                "omic_sizes": train_dataset.omic_sizes,
                "n_classes": 4,
                "fusion": args.fusion,
                "model_size": args.model_size,
                "alpha": args.F_alpha,
                "beta":args.F_beta,
                "tokenS":args.tokenS,
                "GT":args.GT,
                "PT":args.PT,
            }
            model = CMTA(**model_dict)
            criterion = define_loss(args)
            optimizer = define_optimizer(args, model)
            scheduler = define_scheduler(args, optimizer)
            engine = Engine(args, results_dir, fold)
        else:
            raise NotImplementedError(
                "Model [{}] is not implemented".format(args.model)
            )
        # start training
        score, epoch = engine.learning(
            model, train_loader, val_loader, criterion, optimizer, scheduler
        )
        # save best score and epoch for each fold
        best_epoch.append(epoch)
        best_score.append(score)

    # finish training
    # mean and std
    best_epoch.append("~")
    best_epoch.append("~")
    best_score.append(np.mean(best_score[1:6]))
    best_score.append(np.std(best_score[1:6]))

    csv_path = os.path.join(results_dir, "results.csv")
    print("############", csv_path)
    with open(csv_path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(header)
        writer.writerow(best_epoch)
        writer.writerow(best_score)


if __name__ == "__main__":
    args = parse_args()
    results = main(args)
    print("finished!")
